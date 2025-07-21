"""
Supabase service layer for managing Messenger session data
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class SupabaseService:
    """Service class for Supabase operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase credentials not found in environment variables")
            self.client = None
        else:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                self.client = None
    
    def is_connected(self) -> bool:
        """Check if Supabase client is connected"""
        return self.client is not None
    
    def get_sessions(self, limit: int = 20, offset: int = 0, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Retrieve messenger sessions from Supabase by grouping messages by session_id
        
        Args:
            limit: Number of sessions to retrieve
            offset: Number of sessions to skip
            filters: Optional filters to apply
        
        Returns:
            Dict containing sessions data and metadata
        """
        if not self.client:
            return {"sessions": [], "total": 0, "error": "Supabase client not initialized"}
        
        try:
            # Get all messages from the correct table name
            query = self.client.table('chat_sessions_for_dashboard').select('*')
            
            # Apply date filters if provided
            if filters:
                if 'date_from' in filters:
                    query = query.gte('dateTime', filters['date_from'])
                if 'date_to' in filters:
                    query = query.lte('dateTime', filters['date_to'])
                if 'session_id' in filters:
                    query = query.eq('session_id', filters['session_id'])
                if 'contact_id' in filters:
                    query = query.eq('contactID', filters['contact_id'])
            
            # Order by ID to get messages in chronological order (oldest first)
            query = query.order('id', desc=False)
            
            response = query.execute()
            
            if not response.data:
                return {"sessions": [], "total": 0}
            
            # Group messages by session_id
            sessions_dict = {}
            for message in response.data:
                session_id = message['session_id']
                if session_id not in sessions_dict:
                    # Create session object from first message
                    sessions_dict[session_id] = {
                        'id': len(sessions_dict) + 1,  # Generate ID for compatibility
                        'session_id': session_id,
                        'customer_name': f"{message['firstName']} {message['lastName']}",
                        'contact_id': message['contactID'],
                        'conversation_start': message['dateTime'],
                        'last_message_time': message['dateTime'],
                        'message_count': 0,
                        'status': 'active',  # Default status
                        'ai_engaged': False,
                        'messages': [],
                        'qa_status': 'unchecked',
                        'created_at': message['dateTime']
                    }
                
                # Add message to session (messages will be sorted by ID later)
                sessions_dict[session_id]['messages'].append({
                    'id': message['id'],
                    'user_ai': message['userAi'],
                    'message': message['messageStr'],
                    'timestamp': message['dateTime']
                })
                sessions_dict[session_id]['message_count'] += 1
                sessions_dict[session_id]['last_message_time'] = message['dateTime']
                
                # Check if AI was engaged
                if message['userAi'] == 'ai':
                    sessions_dict[session_id]['ai_engaged'] = True
            
            # Process completion status for all sessions
            for session_id, session_data in sessions_dict.items():
                # Check if session contains the booking URL (completed session)
                session_data['completed'] = any(
                    'https://shorturl.at/9u9oh' in str(msg.get('message', ''))
                    for msg in session_data['messages']
                )
            
            # Convert to list and apply filters
            sessions_list = list(sessions_dict.values())
            
            # Apply additional filters after grouping
            if filters:
                if 'completed' in filters:
                    sessions_list = [s for s in sessions_list if s['completed'] == filters['completed']]
                if 'status' in filters:
                    sessions_list = [s for s in sessions_list if s['status'] == filters['status']]
                if 'ai_engaged' in filters:
                    sessions_list = [s for s in sessions_list if s['ai_engaged'] == filters['ai_engaged']]
            
            # Sort by last message time (newest first)
            sessions_list.sort(key=lambda x: x['last_message_time'], reverse=True)
            
            # Apply pagination to the grouped sessions
            total = len(sessions_list)
            paginated_sessions = sessions_list[offset:offset + limit] if sessions_list else []
            
            return {
                "sessions": paginated_sessions,
                "total": total,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error retrieving sessions from Supabase: {str(e)}")
            return {"sessions": [], "total": 0, "error": str(e)}
    
    def get_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific session by ID from Supabase
        
        Args:
            session_id: The session ID to retrieve
        
        Returns:
            Dict containing session data or error
        """
        if not self.client:
            return {"session": None, "error": "Supabase client not initialized"}
        
        try:
            # Get all messages for this session
            response = self.client.table('Chat Sessions Dashboard').select('*').eq('session_id', session_id).order('dateTime', desc=False).execute()
            
            if response.data and len(response.data) > 0:
                return {"session": response.data[0], "error": None}
            else:
                return {"session": None, "error": "Session not found"}
                
        except Exception as e:
            logger.error(f"Error retrieving session {session_id} from Supabase: {str(e)}")
            return {"session": None, "error": str(e)}
    
    def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new session in Supabase
        
        Args:
            session_data: The session data to create
        
        Returns:
            Dict containing created session data or error
        """
        if not self.client:
            return {"session": None, "error": "Supabase client not initialized"}
        
        try:
            response = self.client.table('messenger_sessions').insert(session_data).execute()
            
            if response.data and len(response.data) > 0:
                return {"session": response.data[0], "error": None}
            else:
                return {"session": None, "error": "Failed to create session"}
                
        except Exception as e:
            logger.error(f"Error creating session in Supabase: {str(e)}")
            return {"session": None, "error": str(e)}
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a session in Supabase
        
        Args:
            session_id: The session ID to update
            update_data: The data to update
        
        Returns:
            Dict containing updated session data or error
        """
        if not self.client:
            return {"session": None, "error": "Supabase client not initialized"}
        
        try:
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            response = self.client.table('messenger_sessions').update(update_data).eq('session_id', session_id).execute()
            
            if response.data and len(response.data) > 0:
                return {"session": response.data[0], "error": None}
            else:
                return {"session": None, "error": "Session not found or update failed"}
                
        except Exception as e:
            logger.error(f"Error updating session {session_id} in Supabase: {str(e)}")
            return {"session": None, "error": str(e)}
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get analytics statistics for the dashboard
        
        Returns:
            Dict containing statistics or error
        """
        if not self.client:
            return {"stats": {}, "error": "Supabase client not initialized"}
        
        try:
            # Get total sessions count
            total_response = self.client.table('messenger_sessions').select('id', count='exact').execute()
            total_sessions = total_response.count if hasattr(total_response, 'count') else 0
            
            # Get passed sessions count
            passed_response = self.client.table('messenger_sessions').select('id', count='exact').eq('qa_status', 'passed').execute()
            passed_sessions = passed_response.count if hasattr(passed_response, 'count') else 0
            
            # Get unchecked sessions count
            unchecked_response = self.client.table('messenger_sessions').select('id', count='exact').eq('qa_status', 'unchecked').execute()
            unchecked_sessions = unchecked_response.count if hasattr(unchecked_response, 'count') else 0
            
            # Get issue sessions count
            issues_response = self.client.table('messenger_sessions').select('id', count='exact').eq('qa_status', 'issue').execute()
            issue_sessions = issues_response.count if hasattr(issues_response, 'count') else 0
            
            return {
                "stats": {
                    "total_sessions": total_sessions,
                    "passed": passed_sessions,
                    "unchecked": unchecked_sessions,
                    "issues": issue_sessions
                },
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error retrieving session stats from Supabase: {str(e)}")
            return {"stats": {}, "error": str(e)}

# Global service instance
supabase_service = SupabaseService()