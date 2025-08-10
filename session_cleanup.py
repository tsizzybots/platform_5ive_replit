"""
Session Cleanup Utility - Processes sessions that may have missed real-time AI extraction
This script can be run periodically to ensure no sessions are missed by the real-time system.
"""

import logging
from datetime import datetime, timedelta
from models import MessengerSession, Lead, ChatSessionForDashboard
from ai_lead_extractor import ai_lead_extractor
from app import db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_sessions_needing_processing():
    """
    Find sessions that have messages but may not have been processed by AI extraction
    Returns sessions where:
    1. There are chat messages
    2. Lead record has default/unknown values
    3. Session has been active recently
    """
    # Find sessions with "Unknown" or missing lead data that have recent activity
    sessions_to_process = []
    
    # Get sessions from the last 24 hours with lead records that need updating
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    
    sessions = db.session.query(MessengerSession).filter(
        MessengerSession.last_message_time >= recent_cutoff
    ).all()
    
    for session in sessions:
        # Check if there's a corresponding lead record
        lead = Lead.query.filter_by(session_id=session.session_id).first()
        
        if lead:
            # Check if lead has default/unknown values
            has_unknown_data = (
                lead.full_name in [None, "", "Unknown", "Web Chat User"] or
                (lead.company_name in [None, ""] and lead.email in [None, ""])
            )
            
            if has_unknown_data:
                # Check if there are actual messages that might contain extractable data
                message_count = ChatSessionForDashboard.query.filter_by(
                    session_id=session.session_id
                ).count()
                
                if message_count > 1:  # More than just initial greeting
                    sessions_to_process.append(session.session_id)
                    logger.info(f"Found session needing processing: {session.session_id}")
    
    return sessions_to_process

def process_missed_sessions():
    """
    Process sessions that may have missed real-time AI extraction
    """
    logger.info("Starting cleanup process for sessions that may have missed AI extraction...")
    
    sessions_to_process = find_sessions_needing_processing()
    
    if not sessions_to_process:
        logger.info("No sessions found needing AI extraction processing")
        return
    
    processed_count = 0
    success_count = 0
    
    for session_id in sessions_to_process:
        try:
            logger.info(f"Processing session: {session_id}")
            
            # Run AI extraction
            success = ai_lead_extractor.process_session_for_lead_extraction(session_id)
            
            processed_count += 1
            if success:
                success_count += 1
                logger.info(f"Successfully processed session: {session_id}")
            else:
                logger.warning(f"No new data extracted for session: {session_id}")
                
        except Exception as e:
            logger.error(f"Error processing session {session_id}: {str(e)}")
    
    logger.info(f"Cleanup completed: {success_count}/{processed_count} sessions processed successfully")

if __name__ == "__main__":
    with db.app.app_context():
        process_missed_sessions()