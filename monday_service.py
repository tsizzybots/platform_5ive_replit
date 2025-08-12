"""
Monday.com integration service for sending completed lead information to Monday.com boards.
"""
import os
import json
import requests
import logging
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class MondayService:
    """Service class for Monday.com GraphQL API integration"""
    
    def __init__(self):
        self.api_url = "https://api.monday.com/v2"
        self.api_token = os.getenv('MONDAY_API_TOKEN')
        self.board_id = os.getenv('MONDAY_BOARD_ID')
        
        if not self.api_token:
            logger.warning("MONDAY_API_TOKEN not configured. Monday.com integration disabled.")
        if not self.board_id:
            logger.warning("MONDAY_BOARD_ID not configured. Monday.com integration disabled.")
            
        self.headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        } if self.api_token else {}
    
    def is_configured(self) -> bool:
        """Check if Monday.com integration is properly configured"""
        return bool(self.api_token and self.board_id)
    
    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict]:
        """Make a GraphQL request to Monday.com API"""
        if not self.is_configured():
            logger.error("Monday.com not configured. Missing API token or board ID.")
            return None
            
        try:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
                
            logger.debug(f"Monday.com API request payload: {payload}")
            
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json=payload,
                timeout=30
            )
            
            logger.debug(f"Monday.com API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Monday.com API request failed: {response.status_code} - {response.text}")
                return None
                
            result = response.json()
            logger.debug(f"Monday.com API response: {result}")
            
            if 'errors' in result:
                logger.error(f"Monday.com GraphQL errors: {result['errors']}")
                return None
                
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Monday.com API request exception: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Monday.com API response parsing error: {e}")
            return None
    
    def get_board_structure(self) -> Optional[Dict]:
        """Get board columns and groups for mapping lead data"""
        query = '''
        {
            boards (ids: [%s]) {
                name
                id
                columns {
                    id
                    title
                    type
                }
                groups {
                    id
                    title
                }
            }
        }
        ''' % self.board_id
        
        result = self._make_request(query)
        if result and 'data' in result:
            boards = result['data'].get('boards', [])
            if boards and len(boards) > 0:
                return boards[0]
            else:
                logger.error(f"No boards found for board ID {self.board_id}")
                return None
        return None
    
    def create_lead_item(self, lead_data: Dict, session_data: Dict) -> Optional[Dict]:
        """
        Create a new item in Monday.com board with lead information
        
        Args:
            lead_data: Lead information from database
            session_data: Session metadata (completion time, etc.)
        
        Returns:
            Created item data or None if failed
        """
        if not self.is_configured():
            logger.warning("Monday.com not configured. Skipping lead creation.")
            return None
        
        # Prepare item name (lead name + company)
        item_name = self._format_item_name(lead_data)
        
        # Prepare column values for the Monday.com board
        column_values = self._prepare_column_values(lead_data, session_data)
        
        # GraphQL mutation to create item
        query = '''
        mutation ($boardId: Int!, $itemName: String!, $columnValues: JSON) {
            create_item (
                board_id: $boardId,
                item_name: $itemName,
                column_values: $columnValues
            ) {
                id
                name
                board {
                    id
                    name
                }
                created_at
            }
        }
        '''
        
        variables = {
            "boardId": int(self.board_id),
            "itemName": item_name,
            "columnValues": json.dumps(column_values)
        }
        
        logger.info(f"Creating Monday.com item for lead: {item_name}")
        result = self._make_request(query, variables)
        
        if result and 'data' in result and 'create_item' in result['data']:
            item = result['data']['create_item']
            logger.info(f"Successfully created Monday.com item: {item['id']} - {item['name']}")
            return item
        else:
            logger.error(f"Failed to create Monday.com item for lead: {item_name}")
            return None
    
    def _format_item_name(self, lead_data: Dict) -> str:
        """Format the item name for Monday.com board"""
        name = lead_data.get('full_name', 'Unknown')
        company = lead_data.get('company_name', '')
        
        if company:
            return f"{name} - {company}"
        return name
    
    def _prepare_column_values(self, lead_data: Dict, session_data: Dict) -> Dict:
        """
        Prepare column values for Monday.com board item.
        This maps our lead data to Monday.com column format.
        
        Note: Column IDs will need to be configured based on your specific Monday.com board setup.
        Common column mappings (you'll need to adjust these based on your board):
        """
        column_values = {}
        
        # Basic contact information
        if lead_data.get('email'):
            column_values['email'] = lead_data['email']
        
        if lead_data.get('phone_number'):
            column_values['phone'] = lead_data['phone_number']
        
        # Company information
        if lead_data.get('company_name'):
            column_values['company'] = lead_data['company_name']
        
        # AI-related information
        if lead_data.get('ai_interest_reason'):
            column_values['ai_interest'] = lead_data['ai_interest_reason']
        
        if lead_data.get('ai_implementation_known'):
            column_values['ai_implementation'] = lead_data['ai_implementation_known']
        
        if lead_data.get('ai_budget_allocated'):
            column_values['budget'] = lead_data['ai_budget_allocated']
        
        if lead_data.get('ai_implementation_timeline'):
            column_values['timeline'] = lead_data['ai_implementation_timeline']
        
        # Business information
        if lead_data.get('business_challenges'):
            column_values['challenges'] = lead_data['business_challenges']
        
        if lead_data.get('business_goals_6_12m'):
            column_values['goals'] = lead_data['business_goals_6_12m']
        
        # Session metadata
        if session_data.get('session_id'):
            column_values['session_id'] = session_data['session_id']
        
        if session_data.get('completion_date'):
            # Format date for Monday.com (YYYY-MM-DD)
            completion_date = session_data['completion_date']
            if isinstance(completion_date, str):
                # Parse ISO format and convert to date
                try:
                    dt = datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
                    column_values['completion_date'] = dt.strftime('%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Could not parse completion date: {completion_date}")
            elif isinstance(completion_date, datetime):
                column_values['completion_date'] = completion_date.strftime('%Y-%m-%d')
        
        # Lead source
        column_values['source'] = 'Platform 5ive Chat Widget'
        
        # Status
        column_values['status'] = 'New Lead'
        
        return column_values
    
    def test_connection(self) -> bool:
        """Test Monday.com API connection and board access"""
        if not self.is_configured():
            return False
        
        board_info = self.get_board_structure()
        if board_info:
            logger.info(f"Successfully connected to Monday.com board: {board_info.get('name', 'Unknown')}")
            return True
        else:
            logger.error("Failed to connect to Monday.com or access board")
            return False


# Singleton instance for use throughout the application
monday_service = MondayService()