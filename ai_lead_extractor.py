import json
import os
import logging
from openai import OpenAI
from typing import Dict, Optional, List, Any
from models import Lead, MessengerSession, ChatSessionForDashboard
from app import db
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# Updated to use the newest available GPT model for enhanced lead extraction
# GPT-4o is the current best model for this task with superior context understanding
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class AILeadExtractor:
    def __init__(self):
        self.openai_client = openai_client
        
    def extract_lead_information(self, session_id: str) -> Optional[Dict]:
        """
        Extract lead information from a chat session using OpenAI
        Args:
            session_id: The unique session identifier
        Returns:
            Dictionary containing extracted lead information
        """
        try:
            # Get all messages for the session
            messages = ChatSessionForDashboard.query.filter_by(session_id=session_id).order_by(ChatSessionForDashboard.dateTime.asc()).all()
            
            if not messages:
                logger.warning(f"No messages found for session {session_id}")
                return None
                
            # Format conversation for AI analysis
            conversation = self._format_conversation_for_ai(messages)
            
            # Use OpenAI to extract lead information
            extracted_data = self._analyze_conversation_with_ai(conversation)
            
            if extracted_data:
                # Process the lead data
                self._process_lead_data(session_id, extracted_data)
                return extracted_data
            else:
                logger.warning(f"No lead information extracted for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting lead information for session {session_id}: {str(e)}")
            return None
    
    def _format_conversation_for_ai(self, messages: List) -> str:
        """Format conversation messages for AI analysis with clear question-answer structure"""
        conversation = []
        
        for i, msg in enumerate(messages):
            role = "AI AGENT" if msg.userAi == "ai" else "USER"
            
            # Add conversation flow indicators for question-answer pairs
            if msg.userAi == "ai" and "?" in msg.messageStr:
                conversation.append(f"{role} ASKS: {msg.messageStr}")
            elif msg.userAi == "user" and i > 0 and messages[i-1].userAi == "ai" and "?" in messages[i-1].messageStr:
                conversation.append(f"{role} RESPONDS: {msg.messageStr}")
            else:
                conversation.append(f"{role}: {msg.messageStr}")
        
        return "\n".join(conversation)
    
    def _analyze_conversation_with_ai(self, conversation: str) -> Optional[Dict]:
        """Use OpenAI to analyze the conversation and extract lead information"""
        try:
            system_prompt = """
You are an expert AI conversation analyst specializing in lead qualification data extraction. Analyze conversational patterns where AI agents ask questions and users provide answers.

CONVERSATION ANALYSIS APPROACH:
1. QUESTION-ANSWER MATCHING: When you see patterns like:
   - AI asks: "What's your full name?" → User responds: "John Doe" = Extract full_name: "John Doe"
   - AI asks: "What's your company called?" → User responds: "Tech Corp" = Extract company_name: "Tech Corp"  
   - AI asks: "What's your email?" → User responds: "john@email.com" = Extract email: "john@email.com"

2. DIRECT STATEMENTS: Look for users directly stating information:
   - "My name is Sarah Johnson" = Extract full_name: "Sarah Johnson"
   - "I work at Microsoft" = Extract company_name: "Microsoft"
   - "You can reach me at contact@company.com" = Extract email: "contact@company.com"

3. CONTEXTUAL UNDERSTANDING: 
   - If AI asks a question and user gives a direct response, that response answers the question
   - If AI acknowledges the answer (e.g., "Thanks, John"), this confirms the extraction
   - User responses immediately following AI questions are answers to those questions

EXTRACTION FIELDS:
CONTACT INFO (extract clean values):
- full_name: Person's complete name
- email: Email address  
- phone_number: Phone number
- company_name: Company/organization name

BUSINESS QUALIFICATION (extract full explanations):
- ai_interest_reason: Why they're interested in AI
- business_challenges: Current business challenges they face
- business_goals_6_12m: Their 6-12 month business objectives
- ai_implementation_known: Their knowledge of AI implementation areas
- ai_implementation_timeline: When they want to implement AI

BUDGET STATUS:
- ai_budget_allocated: true/false/null based on budget allocation status

CRITICAL RULES:
- Analyze the FULL conversation flow, not just individual messages
- Match user responses to AI questions that immediately preceded them
- Extract clean contact values, full explanatory responses for business fields
- Only extract explicitly provided information
- Return null for unavailable information

Return valid JSON with extracted data.
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Latest GPT model for superior accuracy
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract lead qualification data from this conversation:\n\n{conversation}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  # Maximum precision for data extraction
                max_tokens=1500   # Increased tokens for comprehensive responses
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"AI extracted lead data: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing conversation with AI: {str(e)}")
            return None
    
    def _process_lead_data(self, session_id: str, extracted_data: Dict) -> None:
        """Process and save the extracted lead data to the database"""
        try:
            # Check if lead record already exists
            existing_lead = Lead.query.filter_by(session_id=session_id).first()
            
            # Clean the extracted data (remove null/empty values)
            clean_data = {k: v for k, v in extracted_data.items() if v is not None and v != ""}
            
            if not clean_data:
                logger.info(f"No valid lead data to process for session {session_id}")
                return
            
            if existing_lead:
                # Update existing lead record
                updated_fields = []
                for field, value in clean_data.items():
                    if hasattr(existing_lead, field):
                        # Update if field is empty, "Unknown", or generic default values
                        current_value = getattr(existing_lead, field)
                        should_update = (
                            current_value is None or 
                            current_value == "" or 
                            current_value == "Unknown" or
                            (field == "full_name" and current_value in ["Web Chat User", "Unknown"])
                        )
                        
                        if should_update:
                            setattr(existing_lead, field, value)
                            updated_fields.append(field)
                
                if updated_fields:
                    existing_lead.updated_at = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"Updated lead for session {session_id}, fields: {', '.join(updated_fields)}")
                else:
                    logger.info(f"No new information to update for session {session_id}")
                    
            else:
                # Create new lead record only if we have a full_name
                if 'full_name' in clean_data:
                    new_lead = Lead(
                        session_id=session_id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Set all available fields
                    for field, value in clean_data.items():
                        if hasattr(new_lead, field):
                            setattr(new_lead, field, value)
                    
                    db.session.add(new_lead)
                    db.session.commit()
                    logger.info(f"Created new lead for session {session_id} with name: {clean_data.get('full_name')}")
                else:
                    logger.info(f"No full_name provided, not creating lead record for session {session_id}")
                    
        except Exception as e:
            logger.error(f"Error processing lead data for session {session_id}: {str(e)}")
            db.session.rollback()
    
    def process_session_for_lead_extraction(self, session_id: str) -> bool:
        """
        Main method to process a session for lead extraction
        Args:
            session_id: The session to process
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            logger.info(f"Starting lead extraction for session: {session_id}")
            extracted_data = self.extract_lead_information(session_id)
            
            if extracted_data:
                logger.info(f"Successfully processed lead extraction for session: {session_id}")
                return True
            else:
                logger.warning(f"No lead data extracted for session: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process session {session_id} for lead extraction: {str(e)}")
            return False

# Create a global instance
ai_lead_extractor = AILeadExtractor()