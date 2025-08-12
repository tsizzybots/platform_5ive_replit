from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import Error, User, MessengerSession, ChatSessionForDashboard, Lead
from schemas import (error_schema, error_query_schema, chat_session_schema,
                     chat_session_update_schema, chat_session_query_schema)
# Using PostgreSQL for all data storage
from marshmallow import ValidationError
from sqlalchemy import and_, or_, func, case, text
from datetime import datetime, timedelta
import pytz
import logging
import os
import requests
from functools import wraps

logger = logging.getLogger(__name__)

# Sydney timezone
SYDNEY_TZ = pytz.timezone('Australia/Sydney')


# Health check endpoint for deployment
@app.route('/health')
def health_check():
    """Health check endpoint for deployment verification"""
    try:
        # Test database connection with timeout
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db.session.commit()  # Ensure connection is active
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'server': 'running',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


# Readiness endpoint for deployment service
@app.route('/ready')
def readiness_check():
    """Readiness check endpoint for deployment service verification"""
    try:
        # More comprehensive readiness check
        from sqlalchemy import text
        
        # Test database connection and basic table existence
        db.session.execute(text('SELECT 1'))
        
        # Check if required tables exist
        result = db.session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('user', 'messenger_session', 'chat_session_for_dashboard')
        """))
        tables = [row[0] for row in result]
        
        db.session.commit()
        
        return jsonify({
            'status': 'ready',
            'database': 'connected',
            'tables_found': len(tables),
            'required_tables': ['user', 'messenger_session', 'chat_session_for_dashboard'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return jsonify({
            'status': 'not_ready',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


# API status endpoint - moved from root to avoid conflict
@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        'message': 'AI Email Helpdesk API',
        'status': 'running',
        'version': '1.0',
        'health_endpoint': '/health',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/conversation/<session_id>', methods=['GET'])
def get_conversation(session_id):
    """Get conversation history excluding the most recent AI message, providing context for AI responses with API key authentication"""
    try:
        # Check for API key in headers
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key.replace('Bearer ', '')
        
        # Get expected API key from environment
        expected_api_key = os.environ.get('CONVERSATION_API_KEY')
        
        if not expected_api_key:
            return jsonify({
                'status': 'error',
                'message': 'API key not configured on server'
            }), 500
            
        if not api_key or api_key != expected_api_key:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or missing API key'
            }), 401
        
        # Validate session ID
        if not session_id:
            return jsonify({
                'status': 'error',
                'message': 'Session ID is required'
            }), 400
        
        # Check if session exists in either table
        messenger_session = MessengerSession.query.filter_by(session_id=session_id).first()
        chat_messages_exist = db.session.query(ChatSessionForDashboard).filter_by(session_id=session_id).first()
        
        if not messenger_session and not chat_messages_exist:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
        
        # Get all messages for this session, ordered by timestamp ascending for chronological order
        all_messages = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=session_id
        ).order_by(ChatSessionForDashboard.dateTime.asc()).all()
        
        if not all_messages:
            return jsonify({
                'status': 'error',
                'message': 'No messages found for this session'
            }), 404
        
        # Check if AI has participated in conversation
        ai_messages = [msg for msg in all_messages if msg.userAi == 'ai']
        if not ai_messages:
            return jsonify({
                'status': 'error',
                'message': 'No AI messages found for this session'
            }), 404
        
        # Exclude the very last AI message from conversation history
        # Find the most recent AI message to exclude
        most_recent_ai = ai_messages[-1] if ai_messages else None
        
        # Find the second-to-last AI message (the one that should appear as last in filtered history)
        second_last_ai = ai_messages[-2] if len(ai_messages) >= 2 else None
        
        # Format conversation history excluding the last AI message
        conversation_history = []
        for message in all_messages:
            # Skip the most recent AI message
            if most_recent_ai and message.id == most_recent_ai.id:
                continue
                
            message_data = {
                'id': message.id,
                'message': message.messageStr or '',
                'timestamp': message.dateTime.isoformat() if message.dateTime else None,
                'sender': 'ai' if message.userAi == 'ai' else 'user'
            }
            conversation_history.append(message_data)
        
        # Get session metadata (excluding the last AI message from counts)
        filtered_messages = [msg for msg in all_messages if not (most_recent_ai and msg.id == most_recent_ai.id)]
        filtered_ai_messages = [msg for msg in filtered_messages if msg.userAi == 'ai']
        
        session_start = all_messages[0].dateTime.isoformat() if all_messages[0].dateTime else None
        # Use the last message in filtered history, or second-to-last overall if last was AI
        session_end = filtered_messages[-1].dateTime.isoformat() if filtered_messages else session_start
        
        # Build comprehensive response with conversation context (excluding last AI message)
        response_data = {
            'session_id': session_id,
            'conversation_history': conversation_history,
            'session_metadata': {
                'total_messages': len(filtered_messages),
                'ai_messages_count': len(filtered_ai_messages),
                'user_messages_count': len(filtered_messages) - len(filtered_ai_messages),
                'session_start': session_start,
                'session_end': session_end,
                'excluded_last_ai_message': True
            },
            # Keep backward compatibility fields - these refer to the last AI message in the filtered history
            'last_ai_message': second_last_ai.messageStr if second_last_ai else (most_recent_ai.messageStr if most_recent_ai else ''),
            'ai_message_time': second_last_ai.dateTime.isoformat() if second_last_ai and second_last_ai.dateTime else (most_recent_ai.dateTime.isoformat() if most_recent_ai and most_recent_ai.dateTime else None)
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error retrieving last AI message for session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve last AI message',
            'error': str(e)
        }), 500


@app.route('/api/lead/<session_id>', methods=['POST', 'PUT'])
def upsert_lead(session_id):
    """Create or update lead information for a session ID with API key authentication"""
    try:
        # Check for API key in headers
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key.replace('Bearer ', '')
        
        # Get expected API key from environment
        expected_api_key = os.environ.get('CONVERSATION_API_KEY')
        
        if not expected_api_key:
            return jsonify({
                'status': 'error',
                'message': 'API key not configured on server'
            }), 500
            
        if not api_key or api_key != expected_api_key:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or missing API key'
            }), 401
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Validate session ID
        if not session_id:
            return jsonify({
                'status': 'error',
                'message': 'Session ID is required'
            }), 400
        
        # Check if lead record already exists
        existing_lead = Lead.query.filter_by(session_id=session_id).first()
        
        if existing_lead:
            # Update existing record
            updated_fields = []
            
            # Update only provided fields
            if 'full_name' in data:
                existing_lead.full_name = data['full_name']
                updated_fields.append('full_name')
            if 'company_name' in data:
                existing_lead.company_name = data['company_name']
                updated_fields.append('company_name')
            if 'email' in data:
                existing_lead.email = data['email']
                updated_fields.append('email')
            if 'phone_number' in data:
                existing_lead.phone_number = data['phone_number']
                updated_fields.append('phone_number')
            if 'ai_interest_reason' in data:
                existing_lead.ai_interest_reason = data['ai_interest_reason']
                updated_fields.append('ai_interest_reason')
            if 'ai_implementation_known' in data:
                existing_lead.ai_implementation_known = data['ai_implementation_known']
                updated_fields.append('ai_implementation_known')
            if 'business_challenges' in data:
                existing_lead.business_challenges = data['business_challenges']
                updated_fields.append('business_challenges')
            if 'business_goals_6_12m' in data:
                existing_lead.business_goals_6_12m = data['business_goals_6_12m']
                updated_fields.append('business_goals_6_12m')
            if 'ai_budget_allocated' in data:
                existing_lead.ai_budget_allocated = data['ai_budget_allocated']
                updated_fields.append('ai_budget_allocated')
            if 'ai_implementation_timeline' in data:
                existing_lead.ai_implementation_timeline = data['ai_implementation_timeline']
                updated_fields.append('ai_implementation_timeline')
            
            # Update timestamp
            existing_lead.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Updated lead for session {session_id}, fields: {', '.join(updated_fields)}")
            
            return jsonify({
                'status': 'success',
                'message': 'Lead updated successfully',
                'action': 'updated',
                'session_id': session_id,
                'updated_fields': updated_fields,
                'lead_id': existing_lead.id
            }), 200
            
        else:
            # Create new record
            new_lead = Lead(
                session_id=session_id,
                full_name=data.get('full_name'),
                company_name=data.get('company_name'),
                email=data.get('email'),
                phone_number=data.get('phone_number'),
                ai_interest_reason=data.get('ai_interest_reason'),
                ai_implementation_known=data.get('ai_implementation_known'),
                business_challenges=data.get('business_challenges'),
                business_goals_6_12m=data.get('business_goals_6_12m'),
                ai_budget_allocated=data.get('ai_budget_allocated'),
                ai_implementation_timeline=data.get('ai_implementation_timeline'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_lead)
            db.session.commit()
            
            logger.info(f"Created new lead for session {session_id}")
            
            return jsonify({
                'status': 'success',
                'message': 'Lead created successfully',
                'action': 'created',
                'session_id': session_id,
                'lead_id': new_lead.id
            }), 201
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error upserting lead for session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to create/update lead',
            'error': str(e)
        }), 500


def get_sydney_time():
    """Get current time in Sydney timezone"""
    return datetime.now(SYDNEY_TZ)


def ensure_messenger_session_exists(session_id):
    """Ensure a messenger session exists for the given session_id"""
    try:
        # Check if messenger session already exists
        messenger_session = MessengerSession.query.filter_by(
            session_id=session_id).first()
        if messenger_session:
            return messenger_session

        # Get chat messages to extract session info
        messages = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=session_id).order_by(
                ChatSessionForDashboard.dateTime).all()

        if not messages:
            return None

        # Extract info from first message
        first_msg = messages[0]
        full_name = 'Unknown'  # Individual messages no longer store names
        contact_id = 'Unknown'  # Contact ID moved to messenger_sessions

        # Calculate session stats
        conversation_start = first_msg.dateTime
        last_message_time = messages[-1].dateTime
        message_count = len(messages)

        # Convert timezone-aware datetimes to UTC naive for storage
        if conversation_start and conversation_start.tzinfo is not None:
            conversation_start = conversation_start.astimezone(
                pytz.UTC).replace(tzinfo=None)
        if last_message_time and last_message_time.tzinfo is not None:
            last_message_time = last_message_time.astimezone(
                pytz.UTC).replace(tzinfo=None)

        # Check if AI engaged and completion status
        ai_engaged = any(msg.userAi == 'ai' for msg in messages)
        has_booking_url = any(
            msg.messageStr and 'within 24 hours' in msg.messageStr.lower()
            for msg in messages)

        if has_booking_url:
            completion_status = 'complete'
            logger.info(f"Auto-sync detected completion for session {session_id} - found 'within 24 hours' message")
        elif ai_engaged:
            # Convert timezone-aware datetime to UTC for comparison
            if last_message_time.tzinfo is not None:
                last_message_utc = last_message_time.astimezone(
                    pytz.UTC).replace(tzinfo=None)
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
            conversation_start=conversation_start,
            last_message_time=last_message_time,
            message_count=message_count,
            status='active',
            completion_status=completion_status,
            ai_engaged=ai_engaged,
            qa_status='unchecked',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow())

        db.session.add(messenger_session)
        
        # Check if lead record already exists (avoid duplicate key constraint)
        existing_lead = Lead.query.filter_by(session_id=session_id).first()
        if not existing_lead:
            # Create corresponding lead record
            lead = Lead(
                session_id=session_id,
                full_name=full_name
            )
            db.session.add(lead)
        
        db.session.commit()

        logger.info(
            f"Auto-created messenger session for session_id: {session_id}")
        return messenger_session

    except Exception as e:
        logger.error(
            f"Error ensuring messenger session exists for {session_id}: {str(e)}"
        )
        db.session.rollback()
        return None


def sync_messenger_session_data(session_id):
    """Sync messenger session data with latest chat messages"""
    try:
        # Find the messenger session
        messenger_session = MessengerSession.query.filter_by(
            session_id=session_id).first()
        if not messenger_session:
            # Create if doesn't exist
            ensure_messenger_session_exists(session_id)
            return

        # Get latest chat data
        message_count = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=session_id).count()

        last_message = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=session_id).order_by(
                ChatSessionForDashboard.dateTime.desc()).first()

        # Check for booking URL completion
        has_booking_url = db.session.query(ChatSessionForDashboard).filter(
            ChatSessionForDashboard.session_id == session_id,
            func.lower(ChatSessionForDashboard.messageStr).contains('within 24 hours')).first() is not None

        completion_status = 'complete' if has_booking_url else 'in_progress'
        
        if has_booking_url:
            logger.info(f"Sync detected completion for session {session_id} - found 'within 24 hours' message")

        # Update messenger session with latest data
        messenger_session.message_count = message_count
        if last_message:
            # Convert timezone-aware datetime to UTC naive for storage
            if last_message.dateTime.tzinfo is not None:
                messenger_session.last_message_time = last_message.dateTime.astimezone(
                    pytz.UTC).replace(tzinfo=None)
            else:
                messenger_session.last_message_time = last_message.dateTime
        messenger_session.completion_status = completion_status
        messenger_session.updated_at = datetime.utcnow()

        db.session.commit()
        logger.info(
            f"Synced messenger session data for: {session_id} - {message_count} messages, status: {completion_status}"
        )

    except Exception as e:
        logger.error(f"Error syncing messenger session {session_id}: {str(e)}")
        db.session.rollback()


def auto_sync_orphaned_sessions():
    """Automatically detect and sync orphaned chat sessions that lack messenger sessions"""
    try:
        # Find sessions in chat_sessions_for_dashboard that don't have messenger_sessions
        orphaned_sessions = db.session.execute(text("""
            SELECT DISTINCT c.session_id
            FROM chat_sessions_for_dashboard c
            LEFT JOIN messenger_sessions m ON c.session_id = m.session_id
            WHERE m.session_id IS NULL
            AND c."dateTime" > NOW() - INTERVAL '24 hours'
        """)).fetchall()

        synced_count = 0
        for row in orphaned_sessions:
            session_id = row[0]
            logger.info(f"Auto-syncing orphaned session: {session_id}")
            
            # Use the existing ensure_messenger_session_exists function
            result = ensure_messenger_session_exists(session_id)
            if result:
                synced_count += 1
                logger.info(f"Successfully synced orphaned session: {session_id}")
            else:
                logger.error(f"Failed to sync orphaned session: {session_id}")

        if synced_count > 0:
            logger.info(f"Auto-sync completed: {synced_count} orphaned sessions synchronized")
        
        return synced_count

    except Exception as e:
        logger.error(f"Error in auto_sync_orphaned_sessions: {str(e)}")
        return 0


@app.route('/api/sync-orphaned-sessions', methods=['POST'])
def sync_orphaned_sessions_endpoint():
    """API endpoint to manually trigger orphaned session sync"""
    try:
        synced_count = auto_sync_orphaned_sessions()
        return jsonify({
            'status': 'success',
            'message': f'Synchronized {synced_count} orphaned sessions',
            'synced_count': synced_count
        })
    except Exception as e:
        logger.error(f"Error in sync endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to sync orphaned sessions',
            'error': str(e)
        }), 500


def auto_update_completion_status():
    """Automatically update completion status for sessions with completion messages"""
    try:
        # Find all sessions that have completion messages but aren't marked as complete
        sessions_to_update = db.session.execute(text("""
            SELECT DISTINCT m.session_id, m.id 
            FROM messenger_sessions m
            WHERE m.completion_status != 'complete'
            AND EXISTS (
                SELECT 1 FROM chat_sessions_for_dashboard c
                WHERE c.session_id = m.session_id
                AND LOWER(c."messageStr") LIKE '%within 24 hours%'
            )
        """)).fetchall()
        
        updated_count = 0
        for row in sessions_to_update:
            session_id = row[0]
            session_db_id = row[1]
            
            # Get latest message info for this session
            latest_message = db.session.query(ChatSessionForDashboard).filter_by(
                session_id=session_id
            ).order_by(ChatSessionForDashboard.dateTime.desc()).first()
            
            message_count = db.session.query(ChatSessionForDashboard).filter_by(
                session_id=session_id
            ).count()
            
            # Update the messenger session
            messenger_session = MessengerSession.query.get(session_db_id)
            if messenger_session:
                messenger_session.completion_status = 'complete'
                messenger_session.message_count = message_count
                if latest_message:
                    # Convert timezone-aware datetime to UTC naive for storage
                    if latest_message.dateTime.tzinfo is not None:
                        messenger_session.last_message_time = latest_message.dateTime.astimezone(
                            pytz.UTC).replace(tzinfo=None)
                    else:
                        messenger_session.last_message_time = latest_message.dateTime
                messenger_session.updated_at = datetime.utcnow()
                
                updated_count += 1
                logger.info(f"Auto-updated completion status for session {session_id}")
        
        if updated_count > 0:
            db.session.commit()
            logger.info(f"Auto-sync: Updated completion status for {updated_count} sessions")
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Error in auto completion status sync: {str(e)}")
        db.session.rollback()
        return 0


@app.route('/api/sync-completion-status', methods=['POST'])
def sync_completion_status_endpoint():
    """API endpoint to manually trigger completion status sync"""
    try:
        updated_count = auto_update_completion_status()
        return jsonify({
            'status': 'success',
            'message': f'Updated completion status for {updated_count} sessions',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error in completion status sync endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to sync completion status',
            'error': str(e)
        }), 500


def require_api_key(f):
    """Decorator to require API key for route access"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.headers.get(
            'Authorization')
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
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    """Decorator to require specific roles for route access"""

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))

            current_user = get_current_user()
            if not current_user or current_user.role not in allowed_roles:
                flash(
                    'Access denied. You do not have permission to access this resource.',
                    'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


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
        # Auto-update completion status before retrieving session details
        auto_update_completion_status()
        # Get the messenger session metadata
        messenger_session = MessengerSession.query.get(session_id)
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Messenger session not found'
            }), 404

        # Get all chat messages for this session
        messages = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=messenger_session.session_id).order_by(
                ChatSessionForDashboard.dateTime).all()

        # Use full name from lead data
        lead = Lead.query.filter_by(session_id=messenger_session.session_id).first()
        full_name = lead.full_name if lead and lead.full_name else 'Unknown'

        # Use stored completion status from database (more reliable than recalculating)
        completion_status = messenger_session.completion_status or 'incomplete'
        
        # Determine AI engagement from messages
        ai_engaged = any(msg.userAi == 'ai' for msg in messages)

        # Build session data
        session_data = {
            'id':
            messenger_session.id,
            'session_id':
            messenger_session.session_id,
            'full_name':
            full_name,
            'contact_id':
            lead.email if lead and lead.email else '',
            'conversation_start':
            messenger_session.conversation_start.isoformat()
            if messenger_session.conversation_start else None,
            'last_message_time':
            messenger_session.last_message_time.isoformat()
            if messenger_session.last_message_time else None,
            'message_count':
            len(messages),
            'status':
            messenger_session.status,
            'ai_engaged':
            messenger_session.ai_engaged,
            'archived':
            messenger_session.status == 'archived',
            'completed':
            completion_status == 'complete',
            'completion_status':
            completion_status,
            'qa_status':
            messenger_session.qa_status,
            'qa_notes':
            messenger_session.qa_notes,
            'qa_status_updated_by':
            messenger_session.qa_status_updated_by,
            'qa_status_updated_at':
            messenger_session.qa_status_updated_at.isoformat()
            if messenger_session.qa_status_updated_at else None,
            'qa_notes_updated_at':
            messenger_session.qa_notes_updated_at.isoformat()
            if messenger_session.qa_notes_updated_at else None,
            'dev_feedback':
            messenger_session.dev_feedback,
            'dev_feedback_by':
            messenger_session.dev_feedback_by,
            'dev_feedback_at':
            messenger_session.dev_feedback_at.isoformat()
            if messenger_session.dev_feedback_at else None,
            'created_at':
            messenger_session.created_at.isoformat()
            if messenger_session.created_at else None,
            'messages': [msg.to_dict() for msg in messages],
            # Add lead data fields for frontend compatibility
            'email': lead.email if lead and lead.email else None,
            'phone_number': lead.phone_number if lead and lead.phone_number else None,
            'company_name': lead.company_name if lead and lead.company_name else None,
            'ai_interest_reason': lead.ai_interest_reason if lead and lead.ai_interest_reason else None,
            'ai_implementation_known': lead.ai_implementation_known if lead and lead.ai_implementation_known else None,
            'business_challenges': lead.business_challenges if lead and lead.business_challenges else None,
            'business_goals_6_12m': lead.business_goals_6_12m if lead and lead.business_goals_6_12m else None,
            'ai_budget_allocated': lead.ai_budget_allocated if lead and lead.ai_budget_allocated else None,
            'ai_implementation_timeline': lead.ai_implementation_timeline if lead and lead.ai_implementation_timeline else None
        }

        return jsonify({'status': 'success', 'data': session_data})

    except Exception as e:
        logger.error(
            f"Error retrieving messenger session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve messenger session',
            'error': str(e)
        }), 500


@app.route('/api/messenger-sessions/<int:session_id>/export', methods=['GET'])
@login_required
def export_messenger_session(session_id):
    """Export messenger session data to a text file - Only for IzzyDev users"""
    try:
        # Check permissions - only allow IzzyDevs user
        current_user = get_current_user()
        if not current_user or current_user.username != 'IzzyDevs':
            return jsonify({
                'status': 'error',
                'message': 'Access denied: Only IzzyDevs user can export sessions'
            }), 403

        # Get the messenger session metadata
        messenger_session = MessengerSession.query.get(session_id)
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Messenger session not found'
            }), 404

        # Get all chat messages for this session
        messages = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=messenger_session.session_id).order_by(
                ChatSessionForDashboard.dateTime).all()

        # Get lead information for this session
        lead = Lead.query.filter_by(session_id=messenger_session.session_id).first()
        full_name = lead.full_name if lead and lead.full_name else 'Unknown'

        # Build the export content
        export_content = []
        export_content.append("=" * 80)
        export_content.append("AI CHAT SESSION EXPORT")
        export_content.append("=" * 80)
        export_content.append("")

        # Session Details
        export_content.append("SESSION DETAILS:")
        export_content.append("-" * 40)
        export_content.append(f"Session ID: {messenger_session.session_id}")
        export_content.append(f"Customer Name: {lead.full_name if lead and lead.full_name else 'Unknown'}")
        export_content.append(f"Company Name: {lead.company_name if lead and lead.company_name else 'Unknown'}")
        export_content.append(f"Email: {lead.email if lead and lead.email else 'Unknown'}")
        export_content.append(f"Phone Number: {lead.phone_number if lead and lead.phone_number else 'Unknown'}")
        export_content.append(
            f"Started: {messenger_session.conversation_start.strftime('%Y-%m-%d %H:%M:%S UTC') if messenger_session.conversation_start else 'N/A'}"
        )
        export_content.append(
            f"Last Message: {messenger_session.last_message_time.strftime('%Y-%m-%d %H:%M:%S UTC') if messenger_session.last_message_time else 'N/A'}"
        )
        export_content.append(f"Total Messages: {len(messages)}")
        export_content.append(
            f"Status: {messenger_session.status or 'Active'}")
        export_content.append(
            f"Completion Status: {messenger_session.completion_status or 'Incomplete'}"
        )
        export_content.append(
            f"QA Status: {messenger_session.qa_status or 'Unchecked'}")
        export_content.append("")

        # Lead qualification details
        if lead:
            export_content.append("LEAD QUALIFICATION DATA:")
            export_content.append("-" * 40)
            export_content.append(f"AI Engaged: {messenger_session.ai_engaged if messenger_session.ai_engaged is not None else 'No'}")
            export_content.append(f"AI Interest Reason: {lead.ai_interest_reason if lead.ai_interest_reason else 'Not answered'}")
            export_content.append(f"AI Implementation Known: {lead.ai_implementation_known if lead.ai_implementation_known else 'Not answered'}")
            export_content.append(f"AI Implementation Timeline: {lead.ai_implementation_timeline if lead.ai_implementation_timeline else 'Not answered'}")
            export_content.append(f"AI Budget Allocated: {lead.ai_budget_allocated if lead.ai_budget_allocated else 'Not answered'}")
            export_content.append(f"Business Goals (6-12m): {lead.business_goals_6_12m if lead.business_goals_6_12m else 'Not answered'}")
            export_content.append(f"Business Challenges: {lead.business_challenges if lead.business_challenges else 'Not answered'}")
        else:
            # No lead record found - show all fields as not answered
            export_content.append("LEAD QUALIFICATION DATA:")
            export_content.append("-" * 40)
            export_content.append(f"AI Engaged: {messenger_session.ai_engaged if messenger_session.ai_engaged is not None else 'No'}")
            export_content.append("AI Interest Reason: Not answered")
            export_content.append("AI Implementation Known: Not answered")  
            export_content.append("AI Implementation Timeline: Not answered")
            export_content.append("AI Budget Allocated: Not answered")
            export_content.append("Business Goals (6-12m): Not answered")
            export_content.append("Business Challenges: Not answered")
        
        export_content.append("")

        # Conversation Thread
        export_content.append("CONVERSATION THREAD:")
        export_content.append("-" * 40)
        export_content.append("")

        if messages:
            for msg in messages:
                timestamp = msg.dateTime.strftime(
                    '%Y-%m-%d %H:%M:%S UTC'
                ) if msg.dateTime else 'Unknown Time'

                if msg.userAi == 'ai':
                    export_content.append(
                        f"[{timestamp}] Platform 5ive AI Agent:")
                else:
                    user_name = 'User'  # Individual messages no longer store user names
                    export_content.append(f"[{timestamp}] {user_name}:")

                # Format message content with proper line breaks
                message_text = msg.messageStr or ''
                for line in message_text.split('\n'):
                    export_content.append(f"  {line}")
                export_content.append("")
        else:
            export_content.append("No messages available")
            export_content.append("")

        # Session Feedback (QA Notes)
        export_content.append("SESSION FEEDBACK (QA NOTES):")
        export_content.append("-" * 40)
        if messenger_session.qa_notes:
            export_content.append(messenger_session.qa_notes)
            if messenger_session.qa_status_updated_by:
                export_content.append("")
                export_content.append(
                    f"Reviewed by: {messenger_session.qa_status_updated_by}")
                if messenger_session.qa_status_updated_at:
                    export_content.append(
                        f"Review Date: {messenger_session.qa_status_updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    )
        else:
            export_content.append("No QA notes available")
        export_content.append("")

        # Developer Feedback (if available)
        if messenger_session.dev_feedback:
            export_content.append("DEVELOPER FEEDBACK:")
            export_content.append("-" * 40)
            export_content.append(messenger_session.dev_feedback)
            if messenger_session.dev_feedback_by:
                export_content.append("")
                export_content.append(
                    f"Developer: {messenger_session.dev_feedback_by}")
                if messenger_session.dev_feedback_at:
                    export_content.append(
                        f"Feedback Date: {messenger_session.dev_feedback_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    )
            export_content.append("")

        # Footer
        export_content.append("=" * 80)
        export_content.append("End of Session Export")
        export_content.append("=" * 80)

        # Join all content with newlines
        final_content = '\n'.join(export_content)

        # Create response with proper headers for file download
        from flask import make_response
        response = make_response(final_content)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers[
            'Content-Disposition'] = f'attachment; filename="session_export_{messenger_session.session_id}_{datetime.utcnow().strftime("%Y%m%d")}.txt"'

        logger.info(
            f"Session exported by {current_user.username}: session {session_id}"
        )
        return response

    except Exception as e:
        logger.error(
            f"Error exporting messenger session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to export messenger session',
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
        logger.error(
            f"Error updating messenger session {session_id}: {str(e)}")
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
        chat_session_ids = db.session.query(
            ChatSessionForDashboard.session_id).distinct().all()
        chat_session_ids = [row[0] for row in chat_session_ids]

        existing_session_ids = db.session.query(
            MessengerSession.session_id).all()
        existing_session_ids = [row[0] for row in existing_session_ids]

        missing_session_ids = [
            sid for sid in chat_session_ids if sid not in existing_session_ids
        ]

        created_count = 0
        for session_id in missing_session_ids:
            if ensure_messenger_session_exists(session_id):
                created_count += 1

        return jsonify({
            'status': 'success',
            'message':
            f'Sync completed. Created {created_count} messenger sessions.',
            'data': {
                'created_count':
                created_count,
                'total_chat_sessions':
                len(chat_session_ids),
                'total_messenger_sessions':
                len(existing_session_ids) + created_count
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
    # Smart auto-sync: Check if any orphaned sessions exist and sync them
    try:
        auto_sync_orphaned_sessions()
        # Auto-update completion status for sessions with completion messages
        auto_update_completion_status()
    except Exception as e:
        logger.warning(f"Auto-sync failed during session fetch, continuing: {str(e)}")

    try:
        query_params = chat_session_query_schema.load(request.args)

        # Pagination
        page = query_params.get('page', 1)
        per_page = query_params.get('per_page', 20)

        # Start with MessengerSession records
        query = db.session.query(
            MessengerSession.id,
            MessengerSession.session_id,
            MessengerSession.conversation_start,
            MessengerSession.last_message_time, MessengerSession.message_count,
            MessengerSession.status, MessengerSession.completion_status,
            MessengerSession.ai_engaged, MessengerSession.qa_status,
            MessengerSession.qa_notes, MessengerSession.qa_status_updated_by,
            MessengerSession.qa_status_updated_at,
            MessengerSession.qa_notes_updated_at,
            MessengerSession.dev_feedback, MessengerSession.dev_feedback_by,
            MessengerSession.dev_feedback_at,
            MessengerSession.created_at.label('created_at'))

        # Apply filters
        if 'date_from' in query_params:
            query = query.filter(MessengerSession.conversation_start >=
                                 query_params['date_from'])
        if 'date_to' in query_params:
            query = query.filter(
                MessengerSession.last_message_time <= query_params['date_to'])
        # Remove email/contact_id filters as these are now in Lead table
        # TODO: Implement filters through Lead table joins if needed
        if 'session_id' in query_params:
            query = query.filter(
                MessengerSession.session_id == query_params['session_id'])
        # Handle completion status filter (independent of archive status)
        if 'completion_status' in query_params and query_params[
                'completion_status'] != 'all':
            query = query.filter(MessengerSession.completion_status ==
                                 query_params['completion_status'])

        # Handle archive status filter (independent of completion status)
        if 'status' in query_params:
            if query_params['status'] == 'all':
                # Show all sessions including archived - no status filter
                pass
            elif query_params['status'] == 'archived':
                query = query.filter(MessengerSession.status == 'archived')
            elif query_params['status'] == 'active':
                query = query.filter(
                    or_(MessengerSession.status == 'active',
                        MessengerSession.status.is_(None)))
            elif query_params['status'] in ['resolved', 'escalated']:
                query = query.filter(
                    MessengerSession.status == query_params['status'])
        elif query_params.get('qa_status'):
            query = query.filter(
                MessengerSession.qa_status == query_params['qa_status'])
        else:
            # Default: show non-archived sessions (active and NULL status)
            query = query.filter(
                or_(MessengerSession.status != 'archived',
                    MessengerSession.status.is_(None)))

        if 'ai_engaged' in query_params:
            query = query.filter(
                MessengerSession.ai_engaged == query_params['ai_engaged'])

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
                session_id=result.session_id).order_by(
                    ChatSessionForDashboard.dateTime).all()

            # Use customer name from Lead record
            lead = Lead.query.filter_by(session_id=result.session_id).first()
            full_name = lead.full_name if lead and lead.full_name else 'Unknown'

            # Get completion status from database (now stored as field)
            completion_status = result.completion_status or 'incomplete'

            # Check if session has booking URL for legacy completed field
            has_booking_url = False
            for msg in messages:
                if msg.messageStr and 'within 24 hours' in msg.messageStr.lower():
                    has_booking_url = True
                    break

            session_data = {
                'id':
                result.id,
                'session_id':
                result.session_id,
                'full_name':
                full_name,
                'contact_id':
                lead.email if lead and lead.email else '',
                'conversation_start':
                result.conversation_start.isoformat()
                if result.conversation_start else None,
                'last_message_time':
                result.last_message_time.isoformat()
                if result.last_message_time else None,
                'message_count':
                result.message_count or 0,
                'completion_status':
                completion_status,
                'completed':
                has_booking_url or completion_status == 'complete',
                'ai_engaged':
                result.ai_engaged
                if result.ai_engaged is not None else ai_engaged,
                'archived':
                result.status == 'archived',
                'status':
                result.status or 'active',
                'qa_status':
                result.qa_status or 'unchecked',
                'qa_notes':
                result.qa_notes,
                'qa_status_updated_by':
                result.qa_status_updated_by,
                'qa_status_updated_at':
                result.qa_status_updated_at.isoformat()
                if result.qa_status_updated_at else None,
                'qa_notes_updated_at':
                result.qa_notes_updated_at.isoformat()
                if result.qa_notes_updated_at else None,
                'dev_feedback':
                result.dev_feedback,
                'dev_feedback_by':
                result.dev_feedback_by,
                'dev_feedback_at':
                result.dev_feedback_at.isoformat()
                if result.dev_feedback_at else None,
                'created_at':
                result.created_at.isoformat() if result.created_at else None,
                'messages': [msg.to_dict() for msg in messages],
                # Add lead data fields for frontend compatibility
                'email': lead.email if lead and lead.email else None,
                'phone_number': lead.phone_number if lead and lead.phone_number else None,
                'company_name': lead.company_name if lead and lead.company_name else None,
                'ai_interest_reason': lead.ai_interest_reason if lead and lead.ai_interest_reason else None,
                'ai_implementation_known': lead.ai_implementation_known if lead and lead.ai_implementation_known else None,
                'business_challenges': lead.business_challenges if lead and lead.business_challenges else None,
                'business_goals_6_12m': lead.business_goals_6_12m if lead and lead.business_goals_6_12m else None,
                'ai_budget_allocated': lead.ai_budget_allocated if lead and lead.ai_budget_allocated else None,
                'ai_implementation_timeline': lead.ai_implementation_timeline if lead and lead.ai_implementation_timeline else None
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
def delete_testing_session(session_id):
    """Delete a testing session from PostgreSQL - only for testing sessions"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
        # Find the session in PostgreSQL messenger_sessions table
        messenger_session = MessengerSession.query.get(session_id)
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404

        session_id_str = messenger_session.session_id

        # Only allow deletion if it's a testing session (check multiple criteria)
        # Get lead information to check names
        lead = Lead.query.filter_by(session_id=messenger_session.session_id).first()
        lead_name = lead.full_name if lead and lead.full_name else 'Unknown'
        
        is_testing_session = (
            lead_name == 'Testing Session' or
            lead_name == 'Unknown' or
            lead_name == 'Web Chat User' or
            lead_name == '' or
            lead_name is None or
            'test' in messenger_session.session_id.lower() or
            'realtime' in messenger_session.session_id.lower() or
            'verification' in messenger_session.session_id.lower() or
            getattr(messenger_session, 'session_source', None) == 'web_chat' or
            messenger_session.session_id.startswith('test_') or
            messenger_session.session_id.startswith('session_')
        )
        
        if not is_testing_session:
            return jsonify({
                'status': 'error',
                'message': 'Can only delete testing sessions'
            }), 403

        logger.info(
            f"Starting deletion of testing session: {session_id} ({session_id_str})"
        )

        # First, delete all chat messages for this session (with count verification)
        deleted_messages = ChatSessionForDashboard.query.filter_by(
            session_id=session_id_str).delete(synchronize_session=False)
        logger.info(
            f"Deleted {deleted_messages} chat messages for session {session_id_str}"
        )

        # Delete associated lead record if it exists
        lead = Lead.query.filter_by(session_id=session_id_str).first()
        if lead:
            db.session.delete(lead)
            logger.info(f"Deleted lead record for session {session_id_str}")

        # Delete the messenger session record
        db.session.delete(messenger_session)
        logger.info(f"Marked messenger session {session_id} for deletion")

        # Force flush to ensure immediate deletion before any auto-sync can interfere
        db.session.flush()
        
        # Double-check that messages are actually deleted before committing
        remaining_messages = ChatSessionForDashboard.query.filter_by(
            session_id=session_id_str).count()
        if remaining_messages > 0:
            logger.error(f"Still found {remaining_messages} messages after deletion attempt for session {session_id_str}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Failed to delete all chat messages'
            }), 500
        
        # Commit all changes atomically
        db.session.commit()
        logger.info(f"All deletion changes committed for session {session_id_str}")

        # Verify deletion was successful
        verification_session = MessengerSession.query.get(session_id)
        verification_messages = ChatSessionForDashboard.query.filter_by(
            session_id=session_id_str).count()

        if verification_session is not None or verification_messages > 0:
            logger.error(
                f"Deletion verification failed for session {session_id}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Deletion verification failed'
            }), 500

        logger.info(
            f"Successfully deleted testing session: {session_id} ({session_id_str}) - Verified removal"
        )
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
    """Get comprehensive statistics for messenger sessions from PostgreSQL with date filtering"""
    try:
        # Auto-update completion status before generating stats
        auto_update_completion_status()
        # Parse query parameters for date filtering
        query_params = request.args

        # Start with base query
        query = MessengerSession.query

        # Apply date filters if provided
        if 'date_from' in query_params and query_params['date_from']:
            try:
                # Handle date format properly - expect YYYY-MM-DD format from frontend
                date_from_str = query_params['date_from']
                if 'T' not in date_from_str:
                    date_from_str += 'T00:00:00'
                date_from = datetime.fromisoformat(
                    date_from_str.replace('Z', '+00:00'))
                query = query.filter(
                    MessengerSession.conversation_start >= date_from)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Invalid date_from format: {query_params['date_from']}, error: {e}"
                )

        if 'date_to' in query_params and query_params['date_to']:
            try:
                # Handle date format properly - expect YYYY-MM-DD format from frontend
                date_to_str = query_params['date_to']
                if 'T' not in date_to_str:
                    date_to_str += 'T23:59:59'
                date_to = datetime.fromisoformat(
                    date_to_str.replace('Z', '+00:00'))
                query = query.filter(
                    MessengerSession.conversation_start <= date_to)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Invalid date_to format: {query_params['date_to']}, error: {e}"
                )

        # Apply status filter to exclude archived sessions by default (unless specifically requested)
        if 'status' in query_params:
            if query_params['status'] == 'all':
                # Show all sessions including archived - no status filter
                pass
            elif query_params['status'] == 'archived':
                query = query.filter(MessengerSession.status == 'archived')
            elif query_params['status'] == 'active':
                query = query.filter(
                    or_(MessengerSession.status == 'active',
                        MessengerSession.status.is_(None)))
            elif query_params['status'] in ['resolved', 'escalated']:
                query = query.filter(
                    MessengerSession.status == query_params['status'])
        else:
            # Default: show non-archived sessions (active and NULL status)
            query = query.filter(
                or_(MessengerSession.status != 'archived',
                    MessengerSession.status.is_(None)))

        # Get filtered messenger sessions for statistics
        messenger_sessions = query.all()

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
@role_required('qa', 'qa_dev', 'admin')
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

        # Update developer feedback if provided (only qa_dev and admin roles)
        if 'dev_feedback' in data:
            if current_user.role in ['qa_dev', 'admin']:
                qa_session.dev_feedback = data['dev_feedback']
                qa_session.dev_feedback_by = current_user.username
                qa_session.dev_feedback_at = sydney_now
            else:
                return jsonify({
                    'status':
                    'error',
                    'message':
                    'Access denied. Only developers can update developer feedback.'
                }), 403

        # If marking as fixed (only qa_dev and admin roles)
        if data.get('mark_fixed', False):
            if current_user.role in ['qa_dev', 'admin']:
                qa_session.qa_status = 'fixed'
                qa_session.qa_status_updated_by = current_user.username
                qa_session.qa_status_updated_at = sydney_now
            else:
                return jsonify({
                    'status':
                    'error',
                    'message':
                    'Access denied. Only developers can mark issues as fixed.'
                }), 403

        qa_session.updated_at = sydney_now
        db.session.commit()

        # Send email notification for QA issues
        if qa_session.qa_status == 'issue':
            try:
                import resend

                resend.api_key = os.environ.get("RESEND_API_KEY")

                # Email content
                subject = f"⚠️ Platform 5ive - QA Issue Detected - Session {qa_session.session_id[:20]}..."

                html_content = f"""
                <html>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f8f9fa;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 20px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 600;">
                                🚨 Platform 5ive
                            </h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">
                                QA Issue Detection Alert
                            </p>
                        </div>
                        
                        <!-- Content -->
                        <div style="padding: 30px;">
                            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
                                <h3 style="margin-top: 0; color: #495057; font-size: 18px;">📋 Session Details</h3>
                                <div style="display: grid; gap: 8px;">
                                    <p style="margin: 5px 0;"><strong style="color: #495057;">Session ID:</strong> <span style="font-family: monospace; background: #e9ecef; padding: 2px 6px; border-radius: 3px;">{qa_session.session_id}</span></p>
                                    <p style="margin: 5px 0;"><strong style="color: #495057;">Customer:</strong> {qa_session.full_name or 'Unknown'}</p>
                                    <p style="margin: 5px 0;"><strong style="color: #495057;">Contact ID:</strong> {qa_session.customer_id or 'N/A'}</p>
                                    <p style="margin: 5px 0;"><strong style="color: #495057;">QA Reviewer:</strong> {qa_session.qa_status_updated_by or 'Unknown'}</p>
                                    <p style="margin: 5px 0;"><strong style="color: #495057;">Detected:</strong> {qa_session.qa_status_updated_at.strftime('%d/%m/%Y %H:%M AEDT') if qa_session.qa_status_updated_at else 'Unknown'}</p>
                                </div>
                            </div>
                            
                            <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; margin: 20px 0;">
                                <h3 style="margin-top: 0; color: #856404; font-size: 18px;">⚠️ QA Notes</h3>
                                <div style="background: white; padding: 15px; border-radius: 5px; border-left: 3px solid #ffc107;">
                                    <p style="white-space: pre-wrap; margin: 0; font-style: italic;">{qa_session.qa_notes or 'No additional notes provided.'}</p>
                                </div>
                            </div>
                            
                            <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0066cc;">
                                <h3 style="margin-top: 0; color: #0066cc; font-size: 18px;">🎯 Next Steps</h3>
                                <ul style="margin: 10px 0; padding-left: 20px;">
                                    <li style="margin: 8px 0; color: #495057;">Review the conversation in the dashboard</li>
                                    <li style="margin: 8px 0; color: #495057;">Investigate the AI's response quality</li>
                                    <li style="margin: 8px 0; color: #495057;">Provide developer feedback if needed</li>
                                    <li style="margin: 8px 0; color: #495057;">Mark as "Fixed" when resolved</li>
                                </ul>
                            </div>
                            
                            <div style="text-align: center; margin: 40px 0;">
                                <a href="https://stay-golden-health-messenger-sessions.replit.app/" 
                                   style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: 600; font-size: 16px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); transition: all 0.3s ease;">
                                    🔍 View in Dashboard
                                </a>
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
                            <p style="font-size: 13px; color: #6c757d; margin: 0;">
                                This is an automated notification from <strong>Platform 5ive</strong> AI Lead Generation Dashboard.
                            </p>
                            <p style="font-size: 12px; color: #adb5bd; margin: 10px 0 0 0;">
                                If you have any questions, please contact our support team.
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Plain text version
                text_content = f"""
PLATFORM 5IVE - QA ISSUE DETECTED

Session Details:
- Session ID: {qa_session.session_id}
- Customer: {qa_session.full_name or 'Unknown'}
- Contact ID: {qa_session.customer_id or 'N/A'}
- QA Reviewer: {qa_session.qa_status_updated_by or 'Unknown'}
- Detected: {qa_session.qa_status_updated_at.strftime('%d/%m/%Y %H:%M AEDT') if qa_session.qa_status_updated_at else 'Unknown'}

QA Notes:
{qa_session.qa_notes or 'No additional notes provided.'}

Dashboard: https://stay-golden-health-messenger-sessions.replit.app/

Please review this issue in the dashboard and provide appropriate feedback.

---
This is an automated notification from Platform 5ive AI Lead Generation Dashboard.
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
                logger.info(
                    f"Successfully sent QA issue email notification for session {session_id}: {response}"
                )

            except Exception as email_error:
                logger.error(
                    f"Failed to send email notification for session {session_id}: {str(email_error)}"
                )
                # Don't fail the main request if email fails

        logger.info(
            f"Updated QA for messenger session {session_id} by {current_user.username}"
        )

        return jsonify({
            'status': 'success',
            'message': 'QA information updated successfully',
            'data': {
                'id':
                qa_session.id,
                'session_id':
                qa_session.session_id,
                'qa_status':
                qa_session.qa_status,
                'qa_notes':
                qa_session.qa_notes,
                'qa_status_updated_by':
                qa_session.qa_status_updated_by,
                'qa_status_updated_at':
                qa_session.qa_status_updated_at.isoformat()
                if qa_session.qa_status_updated_at else None
            }
        })

    except Exception as e:
        logger.error(
            f"Error updating QA for messenger session {session_id}: {str(e)}")
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
            query = query.filter(
                Error.workflow.ilike(f"%{query_params['workflow']}%"))

        if 'date_from' in query_params:
            query = query.filter(Error.timestamp >= query_params['date_from'])

        if 'date_to' in query_params:
            query = query.filter(Error.timestamp <= query_params['date_to'])

        # Order by timestamp (newest first)
        query = query.order_by(Error.timestamp.desc())

        # Pagination
        page = query_params.get('page', 1)
        per_page = query_params.get('per_page', 20)

        paginated = query.paginate(page=page,
                                   per_page=per_page,
                                   error_out=False)

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
    """Get daily statistics for messenger sessions from PostgreSQL with date filtering"""
    try:
        # Parse query parameters for date filtering
        query_params = request.args

        # Default to last 7 days if no date range provided
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(
            days=6)  # 7 days total including today

        # Override with provided date range if available
        if 'date_from' in query_params and query_params['date_from']:
            try:
                date_from_str = query_params['date_from']
                if 'T' not in date_from_str:
                    date_from_str += 'T00:00:00'
                start_date = datetime.fromisoformat(
                    date_from_str.replace('Z', '+00:00')).date()
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Invalid date_from format in daily stats: {query_params['date_from']}"
                )

        if 'date_to' in query_params and query_params['date_to']:
            try:
                date_to_str = query_params['date_to']
                if 'T' not in date_to_str:
                    date_to_str += 'T23:59:59'
                end_date = datetime.fromisoformat(
                    date_to_str.replace('Z', '+00:00')).date()
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Invalid date_to format in daily stats: {query_params['date_to']}"
                )

        # Get messenger sessions filtered by date range
        query = MessengerSession.query.filter(
            MessengerSession.conversation_start
            >= datetime.combine(start_date, datetime.min.time()),
            MessengerSession.conversation_start
            <= datetime.combine(end_date, datetime.max.time()))

        # Apply status filter to exclude archived sessions by default (unless specifically requested)
        if 'status' in query_params:
            if query_params['status'] == 'all':
                pass  # Show all sessions including archived
            elif query_params['status'] == 'archived':
                query = query.filter(MessengerSession.status == 'archived')
            elif query_params['status'] == 'active':
                query = query.filter(
                    or_(MessengerSession.status == 'active',
                        MessengerSession.status.is_(None)))
        else:
            # Default: show non-archived sessions (active and NULL status)
            query = query.filter(
                or_(MessengerSession.status != 'archived',
                    MessengerSession.status.is_(None)))

        messenger_sessions = query.all()

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
                        if qa_status in [
                                'passed', 'unchecked', 'issue', 'fixed'
                        ]:
                            daily_stats[date_key][qa_status] += 1

        # Convert to list and sort by date
        daily_list = list(daily_stats.values())
        daily_list.sort(key=lambda x: x['date'])

        return jsonify({'status': 'success', 'data': daily_list})

    except Exception as e:
        logger.error(f"Error getting daily messenger session stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get daily statistics',
            'error': str(e)
        }), 500


@app.route('/api/messenger-sessions/<session_id>/sync', methods=['POST'])
def sync_single_messenger_session(session_id):
    """Manually sync a specific messenger session with latest chat data"""
    try:
        sync_messenger_session_data(session_id)
        return jsonify({
            'status': 'success',
            'message': f'Session {session_id} synced successfully'
        })
    except Exception as e:
        logger.error(f"Error syncing session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to sync session',
            'error': str(e)
        }), 500


# Web Chat Routes
@app.route('/chat')
def web_chat():
    """Serve the web chat interface"""
    return render_template('chat.html')


@app.route('/embed-chat')
def embed_chat():
    """Serve the embeddable chat widget for iframe"""
    return render_template('embed_chat.html')


@app.route('/api/embed-chat/send-message', methods=['POST'])
def embed_chat_send_message():
    """Production endpoint for embed chat to send messages to AI agent"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'message' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Message is required'
            }), 400
            
        message = data['message'].strip()
        if not message:
            return jsonify({
                'status': 'error', 
                'message': 'Message cannot be empty'
            }), 400
            
        session_id = data.get('sessionId')
        first_name = data.get('firstName', 'Website')
        last_name = data.get('lastName', 'Visitor')  
        contact_id = data.get('contactId', 'embed_visitor')
        
        # Prepare webhook payload matching the test AI format
        payload = {
            "action": "sendMessage",
            "chatInput": message,
            "firstName": first_name,
            "lastName": last_name,
            "contactID": contact_id
        }
        
        # Only include sessionId if we have one from previous messages
        if session_id:
            payload["sessionId"] = session_id
            
        # Send to the same webhook as test AI
        webhook_url = 'https://n8n-g0cw.onrender.com/webhook/44e68b37-d078-44b3-b3bc-2a51a9822aca'
        
        logger.info(f"=== EMBED CHAT WEBHOOK REQUEST ===")
        logger.info(f"URL: {webhook_url}")
        logger.info(f"User Message: {message}")
        logger.info(f"Payload: {payload}")
        
        import requests
        webhook_response = requests.post(
            webhook_url,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout=30
        )
        
        logger.info(f"=== WEBHOOK RESPONSE ===")
        logger.info(f"Status: {webhook_response.status_code}")
        
        if not webhook_response.ok:
            logger.error(f"Webhook error response: {webhook_response.text}")
            # Provide fallback response when webhook is down
            import time
            return jsonify({
                'status': 'success',
                'sessionId': session_id or f'session_{int(time.time())}',
                'aiResponse': 'Hi! Thanks for reaching out. Our AI system is temporarily unavailable, but I wanted to let you know we received your message. Please provide your contact details and we\'ll get back to you shortly.',
                'error': f'Webhook temporarily unavailable (status: {webhook_response.status_code})'
            })
            
        try:
            ai_response = webhook_response.json()
            logger.info(f"AI Response: {ai_response}")
            
            # Extract session ID from response for future messages
            response_session_id = ai_response.get('sessionId', session_id)
            
            # Extract AI message from response - handle different formats
            ai_message = ''
            if ai_response.get('aiResponse'):
                ai_message = ai_response['aiResponse']
            elif ai_response.get('message'):
                ai_message = ai_response['message'] 
            elif ai_response.get('response'):
                ai_message = ai_response['response']
            elif isinstance(ai_response, str):
                ai_message = ai_response
            else:
                ai_message = 'I received your message. How can I help you further?'
            
            # Note: Database storage happens via webhook callback to /api/webhook/chat-session
            # The webhook flow handles all database operations automatically
                
            return jsonify({
                'status': 'success',
                'sessionId': response_session_id,
                'aiResponse': ai_message,
                'data': ai_response
            })
            
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing webhook response: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid response from AI agent',
                'error': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error in embed chat send message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500


@app.route('/preview/chat')
def preview_chat():
    """Preview the chat widget exactly as it will appear on WordPress"""
    return render_template('chat_preview.html')


@app.route('/demo/email-template')
def demo_email_template():
    """Demo page to preview the QA issue email template with Platform 5ive branding"""
    # Generate sample email content with dummy data
    html_content = """
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f8f9fa;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 20px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 600;">
                    🚨 Platform 5ive
                </h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">
                    QA Issue Detection Alert
                </p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
                    <h3 style="margin-top: 0; color: #495057; font-size: 18px;">📋 Session Details</h3>
                    <div style="display: grid; gap: 8px;">
                        <p style="margin: 5px 0;"><strong style="color: #495057;">Session ID:</strong> <span style="font-family: monospace; background: #e9ecef; padding: 2px 6px; border-radius: 3px;">session_demo_p5ive_2025080814</span></p>
                        <p style="margin: 5px 0;"><strong style="color: #495057;">Customer:</strong> Sarah Johnson</p>
                        <p style="margin: 5px 0;"><strong style="color: #495057;">Contact ID:</strong> 987654321</p>
                        <p style="margin: 5px 0;"><strong style="color: #495057;">QA Reviewer:</strong> Platform5ive QA Team</p>
                        <p style="margin: 5px 0;"><strong style="color: #495057;">Detected:</strong> 08/08/2025 14:30 AEDT</p>
                    </div>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404; font-size: 18px;">⚠️ QA Notes</h3>
                    <div style="background: white; padding: 15px; border-radius: 5px; border-left: 3px solid #ffc107;">
                        <p style="white-space: pre-wrap; margin: 0; font-style: italic;">AI response provided generic lead generation information instead of addressing the customer's specific inquiry about healthcare sector targeting and compliance requirements. The response missed key opportunities to qualify the lead and gather relevant healthcare industry details. Requires review of AI training data and response optimization for healthcare vertical.</p>
                    </div>
                </div>
                
                <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0066cc;">
                    <h3 style="margin-top: 0; color: #0066cc; font-size: 18px;">🎯 Next Steps</h3>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li style="margin: 8px 0; color: #495057;">Review the conversation in the dashboard</li>
                        <li style="margin: 8px 0; color: #495057;">Investigate the AI's response quality</li>
                        <li style="margin: 8px 0; color: #495057;">Provide developer feedback if needed</li>
                        <li style="margin: 8px 0; color: #495057;">Mark as "Fixed" when resolved</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 40px 0;">
                    <a href="https://stay-golden-health-messenger-sessions.replit.app/" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: 600; font-size: 16px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); transition: all 0.3s ease;">
                        🔍 View in Dashboard
                    </a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
                <p style="font-size: 13px; color: #6c757d; margin: 0;">
                    This is an automated notification from <strong>Platform 5ive</strong> AI Lead Generation Dashboard.
                </p>
                <p style="font-size: 12px; color: #adb5bd; margin: 10px 0 0 0;">
                    If you have any questions, please contact our support team.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return html_content


@app.route('/api/chat-message', methods=['POST'])
def handle_chat_message():
    """Handle incoming chat messages from web chat widget"""
    try:
        data = request.get_json()

        # Extract message data
        session_id = data.get('session_id')
        message = data.get('message', '')
        user_type = data.get('user_type', 'user')  # 'user' or 'ai'
        first_name = data.get('firstName', '')
        last_name = data.get('lastName', '')
        contact_id = data.get('contactID', '')
        session_source = data.get('session_source', 'web_chat')

        # Validate required fields
        if not session_id or not message:
            return jsonify({
                'status': 'error',
                'message': 'session_id and message are required'
            }), 400

        # Create chat message record
        chat_message = ChatSessionForDashboard(session_id=session_id,
                                               dateTime=datetime.utcnow(),
                                               userAi=user_type,
                                               messageStr=message)

        db.session.add(chat_message)

        # Always ensure MessengerSession exists and is in sync
        logger.info(f"Processing chat message for session {session_id}, user_type: {user_type}")

        # Ensure MessengerSession exists for this web chat
        messenger_session = MessengerSession.query.filter_by(
            session_id=session_id).first()
        if not messenger_session:
            # Create new session for web chat
            messenger_session = MessengerSession(
                session_id=session_id,
                conversation_start=datetime.utcnow(),
                last_message_time=datetime.utcnow(),
                message_count=1,
                session_source=session_source,
                ai_engaged=(user_type == 'ai'),
                completion_status='in_progress',
                status='active')
            db.session.add(messenger_session)
            
            # Create corresponding lead record
            lead = Lead(
                session_id=session_id,
                full_name=f"{first_name} {last_name}".strip() if first_name or last_name else 'Web Chat User',
                email=contact_id if '@' in contact_id else None
            )
            db.session.add(lead)
        else:
            # Update existing session
            messenger_session.last_message_time = datetime.utcnow()
            messenger_session.message_count = db.session.query(
                ChatSessionForDashboard).filter_by(
                    session_id=session_id).count() + 1

            if user_type == 'ai':
                messenger_session.ai_engaged = True
                
                # Check if this AI message indicates completion (contains booking URL)
                if message and 'within 24 hours' in message.lower():
                    messenger_session.completion_status = 'complete'
                    logger.info(f"Session {session_id} marked as complete due to booking URL message")
                    
                    # Store completion notification for real-time dashboard updates
                    try:
                        # Store in a simple in-memory notification queue (for real-time updates)
                        if not hasattr(app, 'completion_notifications'):
                            app.completion_notifications = []
                        
                        notification = {
                            'session_id': session_id,
                            'timestamp': datetime.utcnow().isoformat(),
                            'message': 'Session completed! Booking URL provided.',
                            'type': 'completion'
                        }
                        app.completion_notifications.append(notification)
                        
                        # Keep only last 50 notifications to prevent memory issues
                        if len(app.completion_notifications) > 50:
                            app.completion_notifications = app.completion_notifications[-50:]
                            
                        logger.info(f"Added completion notification for session {session_id}")
                    except Exception as notify_error:
                        logger.error(f"Error creating completion notification: {notify_error}")

            # Update customer info in lead record if provided
            lead = Lead.query.filter_by(session_id=session_id).first()
            if not lead:
                lead = Lead(session_id=session_id)
                db.session.add(lead)
            
            if first_name or last_name:
                lead.full_name = f"{first_name} {last_name}".strip()
            if contact_id:
                lead.email = contact_id if '@' in contact_id else lead.email

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Chat message saved successfully',
            'session_id': session_id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error handling chat message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to save chat message',
            'error': str(e)
        }), 500


@app.route('/api/completion-notifications', methods=['GET'])
def get_completion_notifications():
    """Get recent completion notifications for real-time dashboard updates"""
    try:
        # Return notifications if any exist
        if hasattr(app, 'completion_notifications') and app.completion_notifications:
            notifications = app.completion_notifications.copy()
            # Clear the notifications after sending them
            app.completion_notifications = []
            return jsonify({
                'status': 'success',
                'notifications': notifications
            })
        else:
            return jsonify({
                'status': 'success', 
                'notifications': []
            })
    except Exception as e:
        logger.error(f"Error getting completion notifications: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get notifications',
            'error': str(e)
        }), 500


@app.route('/api/webhook-delivery', methods=['POST'])
def handle_webhook_delivery():
    """Handle webhook delivery for completed lead generation sessions"""
    try:
        data = request.get_json()

        # Extract webhook data
        session_id = data.get('session_id')
        name = data.get('name', '')
        email = data.get('email', '')
        chat_transcript = data.get('chat_transcript', [])
        completed = data.get('completed', False)
        source = data.get('source', 'web_chat')

        # Validate required fields
        if not session_id:
            return jsonify({
                'status': 'error',
                'message': 'session_id is required'
            }), 400

        # Get or create MessengerSession
        messenger_session = MessengerSession.query.filter_by(
            session_id=session_id).first()
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404

        # Update lead data
        lead = Lead.query.filter_by(session_id=session_id).first()
        if not lead:
            lead = Lead(session_id=session_id)
            db.session.add(lead)
        
        if name:
            lead.full_name = name
        if email:
            lead.email = email

        if completed:
            messenger_session.completion_status = 'complete'

        # Prepare webhook payload
        webhook_payload = {
            'session_id': session_id,
            'name': name,
            'email': email,
            'chat_transcript': chat_transcript,
            'completed': completed,
            'source': source,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Get webhook URL from environment (can be configured later)
        webhook_url = os.environ.get('N8N_WEBHOOK_URL')

        if webhook_url:
            try:
                # Send to webhook
                webhook_response = requests.post(
                    webhook_url,
                    json=webhook_payload,
                    timeout=30,
                    headers={'Content-Type': 'application/json'})

                # Update session with webhook delivery status
                messenger_session.webhook_delivered = webhook_response.status_code == 200
                messenger_session.webhook_delivery_at = datetime.utcnow()
                messenger_session.webhook_url = webhook_url
                messenger_session.webhook_response = f"Status: {webhook_response.status_code}, Response: {webhook_response.text[:500]}"

                db.session.commit()

                return jsonify({
                    'status': 'success',
                    'message': 'Webhook delivered successfully',
                    'webhook_status': webhook_response.status_code,
                    'session_updated': True
                })

            except requests.exceptions.RequestException as e:
                # Webhook failed, but still update session
                messenger_session.webhook_delivered = False
                messenger_session.webhook_delivery_at = datetime.utcnow()
                messenger_session.webhook_url = webhook_url
                messenger_session.webhook_response = f"Error: {str(e)}"

                db.session.commit()

                return jsonify({
                    'status': 'warning',
                    'message': 'Session updated but webhook delivery failed',
                    'error': str(e),
                    'session_updated': True
                }), 200
        else:
            # No webhook URL configured, just update session
            messenger_session.webhook_delivered = False
            messenger_session.webhook_delivery_at = datetime.utcnow()
            messenger_session.webhook_response = "No webhook URL configured"

            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': 'Session updated (no webhook configured)',
                'session_updated': True
            })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error handling webhook delivery: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to process webhook delivery',
            'error': str(e)
        }), 500


@app.route('/api/sessions/<session_id>/export', methods=['GET'])
@login_required
def export_session(session_id):
    """Export session data as a formatted text file - Only for IzzyDevs user"""
    try:
        from flask import make_response
        
        # Check permissions - only allow IzzyDevs user
        current_user = get_current_user()
        if not current_user or current_user.username != 'IzzyDevs':
            return jsonify({
                'status': 'error',
                'message': 'Access denied: Only IzzyDevs user can export sessions'
            }), 403

        # Get session data
        messenger_session = MessengerSession.query.filter_by(
            session_id=session_id).first()
        if not messenger_session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404

        # Get chat messages
        chat_messages = db.session.query(ChatSessionForDashboard).filter_by(
            session_id=session_id).order_by(
                ChatSessionForDashboard.dateTime).all()

        # Get comprehensive lead information
        lead = Lead.query.filter_by(session_id=session_id).first()

        # Format export content
        export_content = []
        export_content.append("=" * 80)
        export_content.append("AI CHAT SESSION EXPORT")
        export_content.append("=" * 80)
        export_content.append("")

        # Session details
        export_content.append("SESSION DETAILS:")
        export_content.append("-" * 40)
        export_content.append(f"Session ID: {messenger_session.session_id}")
        export_content.append(f"Customer Name: {lead.full_name if lead and lead.full_name else 'Unknown'}")
        export_content.append(f"Company Name: {lead.company_name if lead and lead.company_name else 'Unknown'}")
        export_content.append(f"Email: {lead.email if lead and lead.email else 'Unknown'}")
        export_content.append(f"Phone Number: {lead.phone_number if lead and lead.phone_number else 'Unknown'}")

        # Format dates in UTC
        start_time = messenger_session.conversation_start
        if start_time:
            export_content.append(
                f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        last_time = messenger_session.last_message_time
        if last_time:
            export_content.append(
                f"Last Message: {last_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        export_content.append(f"Total Messages: {messenger_session.message_count}")
        export_content.append(f"Status: {messenger_session.status}")
        export_content.append(f"Completion Status: {messenger_session.completion_status}")
        export_content.append(f"QA Status: {messenger_session.qa_status}")
        export_content.append("")

        # Lead qualification details
        if lead:
            export_content.append("LEAD QUALIFICATION DATA:")
            export_content.append("-" * 40)
            export_content.append(f"AI Engaged: {messenger_session.ai_engaged if messenger_session.ai_engaged is not None else 'No'}")
            export_content.append(f"AI Interest Reason: {lead.ai_interest_reason if lead.ai_interest_reason else 'Not answered'}")
            export_content.append(f"AI Implementation Known: {lead.ai_implementation_known if lead.ai_implementation_known else 'Not answered'}")
            export_content.append(f"AI Implementation Timeline: {lead.ai_implementation_timeline if lead.ai_implementation_timeline else 'Not answered'}")
            export_content.append(f"AI Budget Allocated: {lead.ai_budget_allocated if lead.ai_budget_allocated else 'Not answered'}")
            export_content.append(f"Business Goals (6-12m): {lead.business_goals_6_12m if lead.business_goals_6_12m else 'Not answered'}")
            export_content.append(f"Business Challenges: {lead.business_challenges if lead.business_challenges else 'Not answered'}")
        else:
            # No lead record found - show all fields as not answered
            export_content.append("LEAD QUALIFICATION DATA:")
            export_content.append("-" * 40)
            export_content.append(f"AI Engaged: {messenger_session.ai_engaged if messenger_session.ai_engaged is not None else 'No'}")
            export_content.append("AI Interest Reason: Not answered")
            export_content.append("AI Implementation Known: Not answered")  
            export_content.append("AI Implementation Timeline: Not answered")
            export_content.append("AI Budget Allocated: Not answered")
            export_content.append("Business Goals (6-12m): Not answered")
            export_content.append("Business Challenges: Not answered")
        
        export_content.append("")

        # Conversation thread
        export_content.append("CONVERSATION THREAD:")
        export_content.append("-" * 40)
        export_content.append("")

        if chat_messages:
            for message in chat_messages:
                user_type = "AI Agent" if message.userAi == 'ai' else "User"
                if message.userAi == 'ai':
                    user_name = "IzzyBots AI Agent"  # You can customize this based on your branding
                else:
                    user_name = "User"  # Individual messages no longer store user names

                timestamp = message.dateTime.strftime(
                    '%Y-%m-%d %H:%M:%S'
                ) if message.dateTime else 'Unknown time'
                export_content.append(f"[{timestamp}] {user_name}:")
                export_content.append(f"  {message.messageStr or ''}")
                export_content.append("")
        else:
            export_content.append("No messages found.")
            export_content.append("")

        # QA Feedback section
        if messenger_session.qa_notes or messenger_session.qa_status != 'unchecked':
            export_content.append("SESSION FEEDBACK (QA NOTES):")
            export_content.append("-" * 40)

            if messenger_session.qa_notes:
                export_content.append(messenger_session.qa_notes)
                export_content.append("")

            if messenger_session.qa_status_updated_by and messenger_session.qa_status_updated_at:
                reviewer = messenger_session.qa_status_updated_by
                review_date = messenger_session.qa_status_updated_at.strftime(
                    '%Y-%m-%d %H:%M:%S')
                export_content.append(
                    f"Reviewed by: {reviewer} on {review_date} UTC")
            export_content.append("")

        # Developer feedback section (if exists)
        if messenger_session.dev_feedback:
            export_content.append("DEVELOPER FEEDBACK:")
            export_content.append("-" * 40)
            export_content.append(messenger_session.dev_feedback)
            export_content.append("")

            if messenger_session.dev_feedback_by and messenger_session.dev_feedback_at:
                dev_user = messenger_session.dev_feedback_by
                dev_date = messenger_session.dev_feedback_at.strftime(
                    '%Y-%m-%d %H:%M:%S')
                export_content.append(
                    f"Developer feedback by: {dev_user} on {dev_date} UTC")
            export_content.append("")

        export_content.append("=" * 80)
        export_content.append("End of Session Export")
        export_content.append("=" * 80)

        # Create response
        export_text = "\n".join(export_content)

        # Create filename with current date
        current_date = datetime.now().strftime('%b %d %Y')
        filename = f"Chat Session Export {current_date}_{session_id}.txt"

        response = make_response(export_text)
        response.headers['Content-Type'] = 'text/plain'
        response.headers[
            'Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error exporting session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to export session',
            'error': str(e)
        }), 500
