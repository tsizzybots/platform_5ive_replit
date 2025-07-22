from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import Error, User, MessengerSession, MessengerSessionQA, ChatSessionForDashboard
from schemas import (error_schema, error_query_schema, chat_session_schema, 
                    chat_session_update_schema, chat_session_query_schema)
# Supabase integration completely removed - now using PostgreSQL only
from marshmallow import ValidationError
from sqlalchemy import and_, or_, func, case
from datetime import datetime, timedelta
import pytz
import logging
import os
import requests
from functools import wraps

logger = logging.getLogger(__name__)

# Sydney timezone
SYDNEY_TZ = pytz.timezone('Australia/Sydney')

def get_sydney_time():
    """Get current time in Sydney timezone"""
    return datetime.now(SYDNEY_TZ)

def ensure_messenger_session_exists(session_id):
    """Ensure a messenger session exists for the given session_id"""
    try:
        # Check if messenger session already exists
        messenger_session = MessengerSession.query.filter_by(session_id=session_id).first()
        if messenger_session:
            return messenger_session
        
        # Get chat messages to extract session info
        messages = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=session_id
        ).order_by(ChatSessionForDashboard.dateTime).all()
        
        if not messages:
            return None
            
        # Extract info from first message
        first_msg = messages[0]
        customer_name = f"{first_msg.firstName} {first_msg.lastName}".strip() if first_msg.firstName and first_msg.lastName else 'Unknown'
        contact_id = first_msg.contactID or 'Unknown'
        
        # Calculate session stats
        conversation_start = first_msg.dateTime
        last_message_time = messages[-1].dateTime
        message_count = len(messages)
        
        # Convert timezone-aware datetimes to UTC naive for storage
        if conversation_start and conversation_start.tzinfo is not None:
            conversation_start = conversation_start.astimezone(pytz.UTC).replace(tzinfo=None)
        if last_message_time and last_message_time.tzinfo is not None:
            last_message_time = last_message_time.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Check if AI engaged and completion status
        ai_engaged = any(msg.userAi == 'ai' for msg in messages)
        has_booking_url = any(msg.messageStr and 'https://shorturl.at/9u9oh' in msg.messageStr for msg in messages)
        
        if has_booking_url:
            completion_status = 'complete'
        elif ai_engaged:
            # Convert timezone-aware datetime to UTC for comparison
            if last_message_time.tzinfo is not None:
                last_message_utc = last_message_time.astimezone(pytz.UTC).replace(tzinfo=None)
            else:
                last_message_utc = last_message_time
            
            if last_message_utc > (datetime.utcnow() - timedelta(hours=12)):
                completion_status = 'in_progress'
            else:
                completion_status = 'incomplete'
        else:
            completion_status = 'incomplete'
        
        # Create new messenger session
        messenger_session = MessengerSession(
            session_id=session_id,
            customer_name=customer_name,
            customer_id=contact_id,
            conversation_start=conversation_start,
            last_message_time=last_message_time,
            message_count=message_count,
            status='active',
            completion_status=completion_status,
            ai_engaged=ai_engaged,
            qa_status='unchecked',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(messenger_session)
        db.session.commit()
        
        logger.info(f"Auto-created messenger session for session_id: {session_id}")
        return messenger_session
        
    except Exception as e:
        logger.error(f"Error ensuring messenger session exists for {session_id}: {str(e)}")
        db.session.rollback()
        return None

def require_api_key(f):
    """Decorator to require API key for route access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key[7:]  # Remove "Bearer " prefix
        
        expected_key = os.environ.get('API_KEY')
        if not expected_key or api_key != expected_key:
            return jsonify({
                'status': 'error', 
                'message': 'Valid API key required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    """Decorator to require login for route access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the current logged-in user"""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session.permanent = True  # Use permanent session
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout the user"""
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@login_required
def index():
    """Render the main interface for testing the API"""
    return render_template('index.html')

@app.route('/api/current-user', methods=['GET'])
@login_required
def get_current_user_api():
    """Get the current logged-in user information"""
    current_user = get_current_user()
    if current_user:
        return jsonify({
            'status': 'success',
            'data': {
                'username': current_user.username,
                'role': current_user.role,
                'logged_in': True
            }
        })
    else:
        return jsonify({
            'status': 'success',
            'data': {
                'username': 'Unknown',
                'logged_in': False
            }
        })

# Messenger Session routes
@app.route('/api/messenger-sessions', methods=['POST'])
@require_api_key
def create_messenger_session():
    """Create a new messenger session"""
    try:
        data = chat_session_schema.load(request.json)
        
        session_obj = MessengerSession(**data)
        db.session.add(session_obj)
        db.session.commit()
        
        logger.info(f"Created new messenger session: {session_obj.id}")
        return jsonify({
            'status': 'success',
            'message': 'Messenger session created successfully',
            'data': chat_session_schema.dump(session_obj)
        }), 201
        
    except ValidationError as e:
        logger.error(f"Validation error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        logger.error(f"Error creating messenger session: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to create messenger session',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions/<int:session_id>', methods=['GET'])
def get_messenger_session(session_id):
    """Get a specific messenger session by ID from PostgreSQL"""
    try:
        # Get the messenger session metadata
        messenger_session = MessengerSession.query.get(session_id)
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Messenger session not found'
            }), 404
        
        # Get all chat messages for this session
        messages = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=messenger_session.session_id
        ).order_by(ChatSessionForDashboard.dateTime).all()
        
        # Build customer name from first message
        customer_name = messenger_session.customer_name or 'Unknown'
        if messages and not customer_name:
            first_msg = messages[0]
            customer_name = f"{first_msg.firstName} {first_msg.lastName}".strip() if first_msg.firstName and first_msg.lastName else 'Unknown'
        
        # Determine completion status
        completion_status = 'incomplete'
        ai_engaged = False
        has_booking_url = False
        
        for msg in messages:
            if msg.userAi == 'ai':
                ai_engaged = True
            if msg.messageStr and 'https://shorturl.at/9u9oh' in msg.messageStr:
                has_booking_url = True
                break
        
        if has_booking_url:
            completion_status = 'complete'
        elif ai_engaged and messages:
            # Use stored completion_status from database
            completion_status = messenger_session.completion_status or 'incomplete'
        
        # Build session data
        session_data = {
            'id': messenger_session.id,
            'session_id': messenger_session.session_id,
            'customer_name': customer_name,
            'contact_id': messenger_session.customer_id,
            'conversation_start': messenger_session.conversation_start.isoformat() if messenger_session.conversation_start else None,
            'last_message_time': messenger_session.last_message_time.isoformat() if messenger_session.last_message_time else None,
            'message_count': len(messages),
            'status': messenger_session.status,
            'ai_engaged': messenger_session.ai_engaged,
            'archived': messenger_session.status == 'archived',
            'completed': has_booking_url,
            'completion_status': completion_status,
            'qa_status': messenger_session.qa_status,
            'qa_notes': messenger_session.qa_notes,
            'qa_status_updated_by': messenger_session.qa_status_updated_by,
            'qa_status_updated_at': messenger_session.qa_status_updated_at.isoformat() if messenger_session.qa_status_updated_at else None,
            'qa_notes_updated_at': messenger_session.qa_notes_updated_at.isoformat() if messenger_session.qa_notes_updated_at else None,
            'dev_feedback': messenger_session.dev_feedback,
            'dev_feedback_by': messenger_session.dev_feedback_by,
            'dev_feedback_at': messenger_session.dev_feedback_at.isoformat() if messenger_session.dev_feedback_at else None,
            'created_at': messenger_session.created_at.isoformat() if messenger_session.created_at else None,
            'messages': [msg.to_dict() for msg in messages]
        }
            
        return jsonify({
            'status': 'success',
            'data': session_data
        })
        
    except Exception as e:
        logger.error(f"Error retrieving messenger session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve messenger session',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions/<int:session_id>', methods=['PUT'])
@login_required
def update_messenger_session(session_id):
    """Update a messenger session"""
    try:
        session_obj = MessengerSession.query.get(session_id)
        if not session_obj:
            return jsonify({
                'status': 'error',
                'message': 'Messenger session not found'
            }), 404
        
        data = chat_session_update_schema.load(request.json)
        
        for key, value in data.items():
            if hasattr(session_obj, key):
                setattr(session_obj, key, value)
        
        session_obj.updated_at = get_sydney_time()
        
        db.session.commit()
        
        logger.info(f"Updated messenger session: {session_obj.id}")
        return jsonify({
            'status': 'success',
            'message': 'Messenger session updated successfully',
            'data': chat_session_schema.dump(session_obj)
        })
        
    except ValidationError as e:
        logger.error(f"Validation error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        logger.error(f"Error updating messenger session {session_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to update messenger session',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions/sync', methods=['POST'])
@require_api_key
def sync_messenger_sessions():
    """Sync chat sessions to messenger sessions - create missing records"""
    try:
        # Get all unique session IDs from chat sessions that don't have messenger sessions
        chat_session_ids = db.session.query(ChatSessionForDashboard.session_id).distinct().all()
        chat_session_ids = [row[0] for row in chat_session_ids]
        
        existing_session_ids = db.session.query(MessengerSession.session_id).all()
        existing_session_ids = [row[0] for row in existing_session_ids]
        
        missing_session_ids = [sid for sid in chat_session_ids if sid not in existing_session_ids]
        
        created_count = 0
        for session_id in missing_session_ids:
            if ensure_messenger_session_exists(session_id):
                created_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Sync completed. Created {created_count} messenger sessions.',
            'data': {
                'created_count': created_count,
                'total_chat_sessions': len(chat_session_ids),
                'total_messenger_sessions': len(existing_session_ids) + created_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error syncing messenger sessions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to sync messenger sessions',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions', methods=['GET'])
def get_messenger_sessions():
    """Get messenger sessions with filtering and pagination - now fully from PostgreSQL"""
    try:
        # Auto-sync: Check for new chat sessions that don't have messenger sessions
        chat_session_ids = db.session.query(ChatSessionForDashboard.session_id).distinct().all()
        chat_session_ids = [row[0] for row in chat_session_ids]
        
        existing_session_ids = db.session.query(MessengerSession.session_id).all()
        existing_session_ids = [row[0] for row in existing_session_ids]
        
        missing_session_ids = [sid for sid in chat_session_ids if sid not in existing_session_ids]
        
        # Auto-create missing messenger sessions
        for session_id in missing_session_ids:
            ensure_messenger_session_exists(session_id)
            logger.info(f"Auto-synced messenger session for: {session_id}")
    except Exception as e:
        logger.warning(f"Auto-sync failed but continuing: {str(e)}")
    
    try:
        query_params = chat_session_query_schema.load(request.args)
        
        # Pagination
        page = query_params.get('page', 1)
        per_page = query_params.get('per_page', 20)
        
        # Start with MessengerSession records and left join chat messages
        query = db.session.query(
            MessengerSession.id.label('messenger_session_id'),
            MessengerSession.session_id,
            MessengerSession.customer_name,
            MessengerSession.customer_id.label('contact_id'),
            MessengerSession.conversation_start,
            MessengerSession.last_message_time,
            MessengerSession.message_count,
            MessengerSession.status,
            MessengerSession.completion_status,
            MessengerSession.ai_engaged,
            MessengerSession.qa_status,
            MessengerSession.qa_notes,
            MessengerSession.qa_status_updated_by,
            MessengerSession.qa_status_updated_at,
            MessengerSession.qa_notes_updated_at,
            MessengerSession.dev_feedback,
            MessengerSession.dev_feedback_by,
            MessengerSession.dev_feedback_at,
            MessengerSession.created_at.label('created_at')
        )
        
        # Apply filters
        if 'date_from' in query_params:
            query = query.filter(MessengerSession.conversation_start >= query_params['date_from'])
        if 'date_to' in query_params:
            query = query.filter(MessengerSession.last_message_time <= query_params['date_to'])
        if 'contact_id' in query_params:
            query = query.filter(MessengerSession.customer_id == query_params['contact_id'])
        if 'session_id' in query_params:
            query = query.filter(MessengerSession.session_id == query_params['session_id'])
        # Handle completion status filter (independent of archive status)
        if 'completion_status' in query_params and query_params['completion_status'] != 'all':
            query = query.filter(MessengerSession.completion_status == query_params['completion_status'])
        
        # Handle archive status filter (independent of completion status)
        if 'status' in query_params:
            if query_params['status'] == 'all':
                # Show all sessions including archived - no status filter
                pass
            elif query_params['status'] == 'archived':
                query = query.filter(MessengerSession.status == 'archived')
            elif query_params['status'] == 'active':
                query = query.filter(or_(MessengerSession.status == 'active', MessengerSession.status.is_(None)))
            elif query_params['status'] in ['resolved', 'escalated']:
                query = query.filter(MessengerSession.status == query_params['status'])
        elif query_params.get('qa_status'):
            query = query.filter(MessengerSession.qa_status == query_params['qa_status'])
        else:
            # Default: show non-archived sessions (active and NULL status)
            query = query.filter(or_(MessengerSession.status != 'archived', MessengerSession.status.is_(None)))
        
        if 'ai_engaged' in query_params:
            query = query.filter(MessengerSession.ai_engaged == query_params['ai_engaged'])
        
        # Get total count before pagination
        total = query.count()
        
        # Order by newest first (created_at descending)
        query = query.order_by(MessengerSession.created_at.desc())
        
        # Apply pagination
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Execute query
        results = query.all()
        
        # Build session data
        sessions = []
        for result in results:
            # Get detailed messages for this session
            messages = db.session.query(ChatSessionForDashboard).filter_by(
                session_id=result.session_id
            ).order_by(ChatSessionForDashboard.dateTime).all()
            
            # Use customer name from MessengerSession record
            customer_name = result.customer_name or 'Unknown'
            
            # Get completion status from database (now stored as field)
            completion_status = result.completion_status or 'incomplete'
            
            # Check if session has booking URL for legacy completed field
            has_booking_url = False
            for msg in messages:
                if msg.messageStr and 'https://shorturl.at/9u9oh' in msg.messageStr:
                    has_booking_url = True
                    break
            
            session_data = {
                'id': result.messenger_session_id,
                'session_id': result.session_id,
                'customer_name': customer_name,
                'contact_id': result.contact_id or '',
                'conversation_start': result.conversation_start.isoformat() if result.conversation_start else None,
                'last_message_time': result.last_message_time.isoformat() if result.last_message_time else None,
                'message_count': result.message_count or 0,
                'completion_status': completion_status,
                'completed': has_booking_url or completion_status == 'complete',
                'ai_engaged': result.ai_engaged if result.ai_engaged is not None else ai_engaged,
                'archived': result.status == 'archived',
                'status': result.status or 'active',
                'qa_status': result.qa_status or 'unchecked',
                'qa_notes': result.qa_notes,
                'qa_status_updated_by': result.qa_status_updated_by,
                'qa_status_updated_at': result.qa_status_updated_at.isoformat() if result.qa_status_updated_at else None,
                'qa_notes_updated_at': result.qa_notes_updated_at.isoformat() if result.qa_notes_updated_at else None,
                'dev_feedback': result.dev_feedback,
                'dev_feedback_by': result.dev_feedback_by,
                'dev_feedback_at': result.dev_feedback_at.isoformat() if result.dev_feedback_at else None,
                'created_at': result.created_at.isoformat() if result.created_at else None,
                'messages': [msg.to_dict() for msg in messages]
            }
            
            sessions.append(session_data)
        
        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        return jsonify({
            'status': 'success',
            'data': sessions,
            'pagination': {
                'page': page,
                'pages': total_pages,
                'per_page': per_page,
                'total': total,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
        
    except ValidationError as e:
        logger.error(f"Query validation error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid query parameters',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        logger.error(f"Error retrieving messenger sessions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve messenger sessions',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_testing_session(session_id):
    """Delete a testing session from PostgreSQL - only for testing sessions"""
    try:
        # Find the session in PostgreSQL messenger_sessions table
        messenger_session = MessengerSession.query.get(session_id)
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
        
        session_id_str = messenger_session.session_id
        
        # Get customer name from chat messages to verify it's a testing session
        first_message = ChatSessionForDashboard.query.filter_by(session_id=session_id_str).first()
        if first_message:
            customer_name = f"{first_message.firstName} {first_message.lastName}".strip()
            
            # Only allow deletion of testing sessions
            if customer_name != 'Testing Session':
                return jsonify({
                    'status': 'error',
                    'message': 'Can only delete testing sessions'
                }), 403
        
        logger.info(f"Starting deletion of testing session: {session_id} ({session_id_str})")
        
        # Delete all chat messages for this session (with count verification)
        deleted_messages = ChatSessionForDashboard.query.filter_by(session_id=session_id_str).delete()
        logger.info(f"Deleted {deleted_messages} chat messages for session {session_id_str}")
        
        # Delete the messenger session record
        db.session.delete(messenger_session)
        logger.info(f"Marked messenger session {session_id} for deletion")
        
        # Commit the changes with explicit flush first
        db.session.flush()
        db.session.commit()
        
        # Verify deletion was successful
        verification_session = MessengerSession.query.get(session_id)
        verification_messages = ChatSessionForDashboard.query.filter_by(session_id=session_id_str).count()
        
        if verification_session is not None or verification_messages > 0:
            logger.error(f"Deletion verification failed for session {session_id}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Deletion verification failed'
            }), 500
        
        logger.info(f"Successfully deleted testing session: {session_id} ({session_id_str}) - Verified removal")
        return jsonify({
            'status': 'success',
            'message': 'Testing session deleted successfully',
            'data': {
                'deleted_session_id': session_id,
                'deleted_session_string_id': session_id_str,
                'deleted_messages_count': deleted_messages
            }
        })
        
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete session',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions/stats', methods=['GET'])
def get_messenger_session_stats():
    """Get comprehensive statistics for messenger sessions from PostgreSQL"""
    try:
        # Get all messenger sessions for statistics
        messenger_sessions = MessengerSession.query.all()
        
        # Calculate statistics
        total_sessions = len(messenger_sessions)
        completed_sessions = 0
        in_progress_sessions = 0
        incomplete_sessions = 0
        passed_sessions = 0
        unchecked_sessions = 0
        issue_sessions = 0
        fixed_sessions = 0
        archived_sessions = 0
        
        for session in messenger_sessions:
            # Calculate completion status based on stored completion_status
            if session.completion_status == 'complete':
                completed_sessions += 1
            elif session.completion_status == 'in_progress':
                in_progress_sessions += 1
            else:
                incomplete_sessions += 1
            
            # Count QA statuses
            qa_status = session.qa_status or 'unchecked'
            if qa_status == 'passed':
                passed_sessions += 1
            elif qa_status == 'issue':
                issue_sessions += 1
            elif qa_status == 'fixed':
                fixed_sessions += 1
            elif qa_status == 'unchecked':
                unchecked_sessions += 1
            
            # Count archived sessions
            if session.status == 'archived':
                archived_sessions += 1
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_sessions': total_sessions,
                'passed': passed_sessions,
                'completed': completed_sessions,
                'in_progress': in_progress_sessions,
                'incomplete': incomplete_sessions,
                'unchecked': unchecked_sessions,
                'issue': issue_sessions,
                'fixed': fixed_sessions,
                'archived': archived_sessions
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting messenger session stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get messenger session statistics',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions/<int:session_id>/qa', methods=['PUT'])
@login_required  
def update_messenger_session_qa(session_id):
    """Update QA status and notes for a messenger session"""
    try:
        # Find the session in PostgreSQL MessengerSession table
        messenger_session = MessengerSession.query.get(session_id)
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
            
        session_id_str = messenger_session.session_id
        
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 401
        
        # Use the existing messenger_session record
        qa_session = messenger_session
        
        data = request.json
        sydney_now = get_sydney_time()
        
        # Update QA status if provided
        if 'qa_status' in data:
            qa_session.qa_status = data['qa_status']
            qa_session.qa_status_updated_by = current_user.username
            qa_session.qa_status_updated_at = sydney_now
        
        # Update QA notes if provided
        if 'qa_notes' in data:
            qa_session.qa_notes = data['qa_notes']
            qa_session.qa_notes_updated_at = sydney_now
            
        # Update QA reviewer if provided
        if 'qa_reviewer' in data:
            qa_session.qa_status_updated_by = data['qa_reviewer']
        
        # Update developer feedback if provided
        if 'dev_feedback' in data:
            qa_session.dev_feedback = data['dev_feedback']
            qa_session.dev_feedback_by = current_user.username
            qa_session.dev_feedback_at = sydney_now
        
        # If marking as fixed
        if data.get('mark_fixed', False):
            qa_session.qa_status = 'fixed'
            qa_session.qa_status_updated_by = current_user.username
            qa_session.qa_status_updated_at = sydney_now
        
        qa_session.updated_at = sydney_now
        db.session.commit()
        
        # Send email notification for QA issues
        if qa_session.qa_status == 'issue':
            try:
                import resend
                
                resend.api_key = os.environ.get("RESEND_API_KEY")
                
                # Email content
                subject = f"⚠️ Stay Golden Health - QA Issue Detected - Session {qa_session.session_id[:20]}..."
                
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 10px;">
                            🚨 Stay Golden Health - QA Issue Detected
                        </h2>
                        
                        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #1976d2;">Session Details</h3>
                            <p><strong>Session ID:</strong> {qa_session.session_id}</p>
                            <p><strong>User Name:</strong> {qa_session.customer_name or 'Unknown'}</p>
                            <p><strong>Contact ID:</strong> {qa_session.customer_id or 'N/A'}</p>
                            <p><strong>QA Reviewer:</strong> {qa_session.qa_status_updated_by or 'Unknown'}</p>
                            <p><strong>Detected:</strong> {qa_session.qa_status_updated_at.strftime('%d/%m/%Y %H:%M') if qa_session.qa_status_updated_at else 'Unknown'}</p>
                        </div>
                        
                        <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #856404;">QA Notes</h3>
                            <p style="white-space: pre-wrap;">{qa_session.qa_notes or 'No additional notes provided.'}</p>
                        </div>
                        
                        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #1976d2;">Next Steps</h3>
                            <ul>
                                <li>Review the conversation in the dashboard</li>
                                <li>Investigate the AI's response quality</li>
                                <li>Provide developer feedback if needed</li>
                                <li>Mark as "Fixed" when resolved</li>
                            </ul>
                        </div>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="https://stay-golden-health-messenger-sessions.replit.app/" 
                               style="background-color: #1976d2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                View in Dashboard
                            </a>
                        </div>
                        
                        <p style="font-size: 12px; color: #666; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">
                            This is an automated notification from the Stay Golden Health AI Messenger Sessions Dashboard.
                        </p>
                    </div>
                </body>
                </html>
                """
                
                # Plain text version
                text_content = f"""
STAY GOLDEN HEALTH - QA ISSUE DETECTED

Session Details:
- Session ID: {qa_session.session_id}
- User Name: {qa_session.customer_name or 'Unknown'}
- Contact ID: {qa_session.customer_id or 'N/A'}
- QA Reviewer: {qa_session.qa_status_updated_by or 'Unknown'}
- Detected: {qa_session.qa_status_updated_at.strftime('%d/%m/%Y %H:%M') if qa_session.qa_status_updated_at else 'Unknown'}

QA Notes:
{qa_session.qa_notes or 'No additional notes provided.'}

Dashboard: https://stay-golden-health-messenger-sessions.replit.app/

Please review this issue in the dashboard and provide appropriate feedback.
                """
                
                # Send email to team
                email_params = {
                    "from": "noreply@izzyagents.ai",
                    "to": ["team@izzyagents.ai"],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content
                }
                
                response = resend.Emails.send(email_params)
                logger.info(f"Successfully sent QA issue email notification for session {session_id}: {response}")
                
            except Exception as email_error:
                logger.error(f"Failed to send email notification for session {session_id}: {str(email_error)}")
                # Don't fail the main request if email fails
        
        logger.info(f"Updated QA for messenger session {session_id} by {current_user.username}")
        
        return jsonify({
            'status': 'success',
            'message': 'QA information updated successfully',
            'data': {
                'id': qa_session.id,
                'session_id': qa_session.session_id,
                'qa_status': qa_session.qa_status,
                'qa_notes': qa_session.qa_notes,
                'qa_status_updated_by': qa_session.qa_status_updated_by,
                'qa_status_updated_at': qa_session.qa_status_updated_at.isoformat() if qa_session.qa_status_updated_at else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating QA for messenger session {session_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to update QA information',
            'error': str(e)
        }), 500

# Error logging routes
@app.route('/api/errors', methods=['POST'])
@require_api_key
def create_error():
    """Create a new error log entry"""
    try:
        data = error_schema.load(request.json)
        
        error = Error(**data)
        db.session.add(error)
        db.session.commit()
        
        logger.info(f"Created new error log: {error.id}")
        return jsonify({
            'status': 'success',
            'message': 'Error logged successfully',
            'data': error_schema.dump(error)
        }), 201
        
    except ValidationError as e:
        logger.error(f"Validation error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        logger.error(f"Error logging error: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to log error',
            'error': str(e)
        }), 500

@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Get error logs with filtering and pagination"""
    try:
        query_params = error_query_schema.load(request.args)
        
        query = Error.query
        
        # Apply filters
        if 'workflow' in query_params:
            query = query.filter(Error.workflow.ilike(f"%{query_params['workflow']}%"))
        
        if 'date_from' in query_params:
            query = query.filter(Error.timestamp >= query_params['date_from'])
        
        if 'date_to' in query_params:
            query = query.filter(Error.timestamp <= query_params['date_to'])
        
        # Order by timestamp (newest first)
        query = query.order_by(Error.timestamp.desc())
        
        # Pagination
        page = query_params.get('page', 1)
        per_page = query_params.get('per_page', 20)
        
        paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': error_schema.dump(paginated.items, many=True),
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'per_page': paginated.per_page,
                'total': paginated.total,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except ValidationError as e:
        logger.error(f"Query validation error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid query parameters',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        logger.error(f"Error retrieving errors: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve errors',
            'error': str(e)
        }), 500

@app.route('/api/messenger-sessions/daily-stats', methods=['GET'])
def get_messenger_session_daily_stats():
    """Get daily statistics for messenger sessions from PostgreSQL"""
    try:
        # Default to last 7 days
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=6)  # 7 days total including today
        
        # Get all messenger sessions
        messenger_sessions = MessengerSession.query.all()
        
        # Create a dictionary to store daily stats
        daily_stats = {}
        
        # Initialize all days with zero counts
        current_date = start_date
        while current_date <= end_date:
            daily_stats[current_date.isoformat()] = {
                'date': current_date.isoformat(),
                'sessions': 0,
                'completed': 0,
                'in_progress': 0,
                'incomplete': 0,
                'passed': 0,
                'unchecked': 0,
                'issue': 0,
                'fixed': 0
            }
            current_date += timedelta(days=1)
        
        # Count sessions by date based on conversation_start
        for session in messenger_sessions:
            if session.conversation_start:
                session_date = session.conversation_start.date()
                if start_date <= session_date <= end_date:
                    date_key = session_date.isoformat()
                    if date_key in daily_stats:
                        daily_stats[date_key]['sessions'] += 1
                        
                        # Count completion status
                        if session.completion_status == 'complete':
                            daily_stats[date_key]['completed'] += 1
                        elif session.completion_status == 'in_progress':
                            daily_stats[date_key]['in_progress'] += 1
                        else:
                            daily_stats[date_key]['incomplete'] += 1
                        
                        # Count QA status
                        qa_status = session.qa_status or 'unchecked'
                        if qa_status in ['passed', 'unchecked', 'issue', 'fixed']:
                            daily_stats[date_key][qa_status] += 1
        
        # Convert to list and sort by date
        daily_list = list(daily_stats.values())
        daily_list.sort(key=lambda x: x['date'])
        
        return jsonify({
            'status': 'success',
            'data': daily_list
        })
        
    except Exception as e:
        logger.error(f"Error getting daily messenger session stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get daily statistics',
            'error': str(e)
        }), 500


