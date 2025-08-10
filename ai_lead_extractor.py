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
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
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
        """Format conversation messages for AI analysis"""
        conversation = []
        for msg in messages:
            role = "AI" if msg.userAi == "ai" else "User"
            conversation.append(f"{role}: {msg.messageStr}")
        
        return "\n".join(conversation)
    
    def _analyze_conversation_with_ai(self, conversation: str) -> Optional[Dict]:
        """Use OpenAI to analyze the conversation and extract lead information"""
        try:
            system_prompt = """
You are an expert lead information extraction system. Analyze the conversation and extract relevant lead information.

EXTRACTION RULES:
1. For SINGLE VALUES (extract clean values only):
   - full_name: Extract just the name (e.g., "John Doe", not "My name is John Doe")
   - email: Extract just the email address
   - phone_number: Extract just the phone number
   - company_name: Extract just the company name

2. For EXPLANATORY FIELDS (extract full user responses):
   - ai_interest_reason: Full explanation of why they're interested in AI
   - business_challenges: Complete description of their challenges
   - business_goals_6_12m: Full explanation of their 6-12 month goals
   - ai_implementation_known: Their complete response about AI implementation knowledge
   - ai_implementation_timeline: Their timeline preference/explanation

3. For BOOLEAN FIELDS:
   - ai_budget_allocated: true if they indicate budget is allocated, false if not, null if unclear

4. Only extract information that is explicitly provided by the user in their responses.
5. Do not infer or assume information that isn't clearly stated.
6. Return null for any field where information wasn't provided.

Respond in JSON format with the extracted fields.
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract lead information from this conversation:\n\n{conversation}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1000
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
                        # Only update if we have new information and field is currently empty or "Unknown"
                        current_value = getattr(existing_lead, field)
                        if current_value is None or current_value == "" or current_value == "Unknown":
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