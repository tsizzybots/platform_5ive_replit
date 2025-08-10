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
You are an advanced lead information extraction system using GPT-4o. Analyze conversations and extract lead qualification data with maximum accuracy.

EXTRACTION RULES:
1. CONTACT FIELDS (extract clean values only):
   - full_name: Extract name only (e.g., "John Doe" from "My name is John Doe")
   - email: Extract email address only
   - phone_number: Extract phone number only  
   - company_name: Extract company name only

2. QUALIFICATION FIELDS (extract full user responses):
   - ai_interest_reason: Complete explanation of their AI interest
   - business_challenges: Full description of current challenges
   - business_goals_6_12m: Complete explanation of 6-12 month business goals
   - ai_implementation_known: Full response about AI implementation areas/knowledge
   - ai_implementation_timeline: Complete timeline preferences and explanation

3. BUDGET FIELD:
   - ai_budget_allocated: true if budget allocated, false if not allocated, null if unclear

CRITICAL REQUIREMENTS:
- Extract ONLY information explicitly stated by the user
- Never infer, assume, or extrapolate information
- Return null for fields where no information was provided
- Be extremely precise with contact information
- Capture full context for business qualification fields

Return valid JSON with all fields.
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
                            (field == "full_name" and current_value == "Web Chat User")
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