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
        self.supabase_key = os.environ.get('SUPABASE_ANON_KEY')
        
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
        Retrieve messenger sessions from Supabase
        
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
            query = self.client.table('messenger_sessions').select('*')
            
            # Apply filters if provided
            if filters:
                if 'status' in filters:
                    query = query.eq('status', filters['status'])
                if 'ai_engaged' in filters:
                    query = query.eq('ai_engaged', filters['ai_engaged'])
                if 'customer_id' in filters:
                    query = query.eq('customer_id', filters['customer_id'])
                if 'qa_status' in filters:
                    query = query.eq('qa_status', filters['qa_status'])
                if 'date_from' in filters:
                    query = query.gte('conversation_start', filters['date_from'])
                if 'date_to' in filters:
                    query = query.lte('conversation_start', filters['date_to'])
            
            # Order by conversation start (newest first) and apply pagination
            query = query.order('conversation_start', desc=True)
            query = query.range(offset, offset + limit - 1)
            
            response = query.execute()
            
            # Get total count for pagination
            count_response = self.client.table('messenger_sessions').select('id', count='exact').execute()
            total = count_response.count if hasattr(count_response, 'count') else 0
            
            return {
                "sessions": response.data,
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
            response = self.client.table('messenger_sessions').select('*').eq('session_id', session_id).execute()
            
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