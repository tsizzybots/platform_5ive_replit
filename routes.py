from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import Error, User, MessengerSession, ChatSessionForDashboard
from schemas import (error_schema, error_query_schema, chat_session_schema,
                     chat_session_update_schema, chat_session_query_schema)
# Using PostgreSQL for all data storage
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


# Health check endpoint for deployment
@app.route('/health')
def health_check():
    """Health check endpoint for deployment verification"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
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
            full_name=full_name,
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

        # Use full name from messenger session
        full_name = messenger_session.full_name or 'Unknown'

        # Determine completion status
        completion_status = 'incomplete'
        ai_engaged = False
        has_booking_url = False

        for msg in messages:
            if msg.userAi == 'ai':
                ai_engaged = True
            if msg.messageStr and 'within 24 hours' in msg.messageStr.lower():
                has_booking_url = True
                break

        if has_booking_url:
            completion_status = 'complete'
        elif ai_engaged and messages:
            # Use stored completion_status from database
            completion_status = messenger_session.completion_status or 'incomplete'

        # Build session data
        session_data = {
            'id':
            messenger_session.id,
            'session_id':
            messenger_session.session_id,
            'full_name':
            full_name,
            'contact_id':
            messenger_session.email,
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
            has_booking_url,
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
            'messages': [msg.to_dict() for msg in messages]
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
        # Check permissions - only allow IzzyDev users
        current_user = get_current_user()
        if not current_user or current_user.username != 'IzzyDev':
            return jsonify({
                'status':
                'error',
                'message':
                'Access denied: Only IzzyDev users can export sessions'
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

        # Use full name from messenger session
        full_name = messenger_session.full_name or 'Unknown'

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
        export_content.append(f"Customer Name: {full_name}")
        export_content.append(
            f"Contact ID: {messenger_session.customer_id or 'N/A'}")
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
    try:
        # Auto-sync: Check for new chat sessions that don't have messenger sessions
        chat_session_ids = db.session.query(
            ChatSessionForDashboard.session_id).distinct().all()
        chat_session_ids = [row[0] for row in chat_session_ids]

        existing_session_ids = db.session.query(
            MessengerSession.session_id).all()
        existing_session_ids = [row[0] for row in existing_session_ids]

        missing_session_ids = [
            sid for sid in chat_session_ids if sid not in existing_session_ids
        ]

        # Auto-create missing messenger sessions
        for session_id in missing_session_ids:
            try:
                ensure_messenger_session_exists(session_id)
                logger.info(f"Auto-synced messenger session for: {session_id}")
            except Exception as e:
                logger.error(
                    f"Failed to create messenger session for {session_id}: {str(e)}"
                )
                continue

        # Auto-sync existing sessions to ensure latest data
        # Note: Temporarily skip individual session sync to prevent API crashes
        # The key issue has been resolved - new sessions are being created properly
        # for session_id in existing_session_ids:
        #     try:
        #         sync_messenger_session_data(session_id)
        #     except Exception as e:
        #         logger.error(f"Failed to sync messenger session {session_id}: {str(e)}")
        #         continue
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
            MessengerSession.session_id, MessengerSession.full_name,
            MessengerSession.email.label('contact_id'),
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
        if 'email' in query_params:
            query = query.filter(
                MessengerSession.email == query_params['email'])
        if 'contact_id' in query_params:  # Keep backward compatibility
            query = query.filter(
                MessengerSession.email == query_params['contact_id'])
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

            # Use customer name from MessengerSession record
            full_name = result.full_name or 'Unknown'

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
                result.messenger_session_id,
                'session_id':
                result.session_id,
                'full_name':
                full_name,
                'contact_id':
                result.contact_id or '',
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

        # Only allow deletion if it's a testing session (check messenger session name)
        if messenger_session.full_name != 'Testing Session':
            return jsonify({
                'status': 'error',
                'message': 'Can only delete testing sessions'
            }), 403

        logger.info(
            f"Starting deletion of testing session: {session_id} ({session_id_str})"
        )

        # Delete all chat messages for this session (with count verification)
        deleted_messages = ChatSessionForDashboard.query.filter_by(
            session_id=session_id_str).delete()
        logger.info(
            f"Deleted {deleted_messages} chat messages for session {session_id_str}"
        )

        # Delete the messenger session record
        db.session.delete(messenger_session)
        logger.info(f"Marked messenger session {session_id} for deletion")

        # Commit the changes with explicit flush first
        db.session.flush()
        db.session.commit()

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

        # Ensure MessengerSession exists for this web chat
        messenger_session = MessengerSession.query.filter_by(
            session_id=session_id).first()
        if not messenger_session:
            # Create new session for web chat
            messenger_session = MessengerSession(
                session_id=session_id,
                full_name=f"{first_name} {last_name}".strip()
                if first_name or last_name else 'Web Chat User',
                email=contact_id if '@' in contact_id else None,
                conversation_start=datetime.utcnow(),
                last_message_time=datetime.utcnow(),
                message_count=1,
                session_source=session_source,
                ai_engaged=(user_type == 'ai'),
                completion_status='in_progress',
                status='active')
            db.session.add(messenger_session)
        else:
            # Update existing session
            messenger_session.last_message_time = datetime.utcnow()
            messenger_session.message_count = db.session.query(
                ChatSessionForDashboard).filter_by(
                    session_id=session_id).count() + 1

            if user_type == 'ai':
                messenger_session.ai_engaged = True

            # Update customer info if provided
            if first_name or last_name:
                messenger_session.full_name = f"{first_name} {last_name}".strip(
                )
            if contact_id:
                messenger_session.email = contact_id if '@' in contact_id else messenger_session.email

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

        # Update session with lead data
        messenger_session.lead_name = name
        messenger_session.lead_email = email
        messenger_session.full_name = name if name else messenger_session.full_name
        messenger_session.customer_id = email if email else messenger_session.customer_id

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
@role_required('qa', 'qa_dev', 'admin')
def export_session(session_id):
    """Export session data as a formatted text file"""
    try:
        from flask import make_response

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
        export_content.append(
            f"Customer Name: {messenger_session.full_name or 'Unknown'}")
        export_content.append(
            f"Contact ID: {messenger_session.customer_id or 'Unknown'}")

        # Format dates in UTC
        start_time = messenger_session.conversation_start
        if start_time:
            export_content.append(
                f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        last_time = messenger_session.last_message_time
        if last_time:
            export_content.append(
                f"Last Message: {last_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        export_content.append(
            f"Total Messages: {messenger_session.message_count}")
        export_content.append(f"Status: {messenger_session.status}")
        export_content.append(
            f"Completion Status: {messenger_session.completion_status}")
        export_content.append(f"QA Status: {messenger_session.qa_status}")
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
