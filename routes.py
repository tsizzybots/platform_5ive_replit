from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import Error, User, ChatSession, MessengerSessionQA
from schemas import (error_schema, error_query_schema, chat_session_schema, 
                    chat_session_update_schema, chat_session_query_schema)
from supabase_service import supabase_service
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
        
        session_obj = ChatSession(**data)
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
    """Get a specific messenger session by ID from Supabase"""
    try:
        # Get all sessions to find the one with matching ID
        result = supabase_service.get_sessions(
            limit=1000,  # Large limit to get all sessions
            offset=0,
            filters={}
        )
        
        if result.get('error'):
            logger.error(f"Supabase error: {result['error']}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve session from database'
            }), 500
        
        sessions = result.get('sessions', [])
        
        # Find the session with the matching ID
        session_data = None
        for session in sessions:
            if session.get('id') == session_id:
                session_data = session
                break
        
        if not session_data:
            return jsonify({
                'status': 'error',
                'message': 'Messenger session not found'
            }), 404
        
        # Sort messages by ID (chronological order - oldest first)
        if 'messages' in session_data:
            session_data['messages'].sort(key=lambda x: x.get('id', 0))
        
        # Get QA data from PostgreSQL if it exists
        session_id_str = session_data.get('session_id')
        if session_id_str:
            qa_session = ChatSession.query.filter_by(session_id=session_id_str).first()
            if qa_session:
                # Merge QA data from PostgreSQL
                session_data.update({
                    'qa_status': qa_session.qa_status,
                    'qa_notes': qa_session.qa_notes,
                    'qa_status_updated_by': qa_session.qa_status_updated_by,
                    'qa_status_updated_at': qa_session.qa_status_updated_at.isoformat() if qa_session.qa_status_updated_at else None,
                    'qa_notes_updated_at': qa_session.qa_notes_updated_at.isoformat() if qa_session.qa_notes_updated_at else None,
                    'dev_feedback': qa_session.dev_feedback,
                    'dev_feedback_by': qa_session.dev_feedback_by,
                    'dev_feedback_at': qa_session.dev_feedback_at.isoformat() if qa_session.dev_feedback_at else None
                })
            
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
@require_api_key
def update_messenger_session(session_id):
    """Update a messenger session"""
    try:
        session_obj = ChatSession.query.get(session_id)
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

@app.route('/api/messenger-sessions', methods=['GET'])
def get_messenger_sessions():
    """Get messenger sessions with filtering and pagination - now from Supabase"""
    try:
        query_params = chat_session_query_schema.load(request.args)
        
        # Prepare filters for Supabase
        filters = {}
        if 'date_from' in query_params:
            filters['date_from'] = query_params['date_from'].isoformat()
        if 'date_to' in query_params:
            filters['date_to'] = query_params['date_to'].isoformat()
        if 'contact_id' in query_params:
            filters['contact_id'] = query_params['contact_id']
        if 'session_id' in query_params:
            filters['session_id'] = query_params['session_id']
        
        # Pagination
        page = query_params.get('page', 1)
        per_page = query_params.get('per_page', 20)
        offset = (page - 1) * per_page
        
        # Get sessions from Supabase
        result = supabase_service.get_sessions(
            limit=per_page,
            offset=offset,
            filters=filters
        )
        
        if result.get('error'):
            logger.error(f"Supabase error: {result['error']}")
            # Fallback to empty result
            sessions = []
            total = 0
        else:
            sessions = result.get('sessions', [])
            total = result.get('total', 0)
            
            # Merge QA data from PostgreSQL for each session
            for session in sessions:
                session_id_str = session.get('session_id')
                if session_id_str:
                    qa_session = ChatSession.query.filter_by(session_id=session_id_str).first()
                    if qa_session:
                        session['qa_status'] = qa_session.qa_status
                        session['qa_notes'] = qa_session.qa_notes
                        session['qa_status_updated_by'] = qa_session.qa_status_updated_by
                        session['qa_status_updated_at'] = qa_session.qa_status_updated_at.isoformat() if qa_session.qa_status_updated_at else None
                        session['qa_notes_updated_at'] = qa_session.qa_notes_updated_at.isoformat() if qa_session.qa_notes_updated_at else None
                        session['dev_feedback'] = qa_session.dev_feedback
                        session['dev_feedback_by'] = qa_session.dev_feedback_by
                        session['dev_feedback_at'] = qa_session.dev_feedback_at.isoformat() if qa_session.dev_feedback_at else None
                    else:
                        session['qa_status'] = 'unchecked'
        
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

@app.route('/api/messenger-sessions/stats', methods=['GET'])
def get_messenger_session_stats():
    """Get comprehensive statistics for messenger sessions from Supabase"""
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Default to last 30 days if no dates provided
        if not date_from:
            date_from_obj = datetime.now(SYDNEY_TZ) - timedelta(days=30)
        else:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            if date_from_obj.tzinfo is None:
                date_from_obj = SYDNEY_TZ.localize(date_from_obj)
        
        if not date_to:
            date_to_obj = datetime.now(SYDNEY_TZ)
        else:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            if date_to_obj.tzinfo is None:
                date_to_obj = SYDNEY_TZ.localize(date_to_obj)
        
        # Prepare filters for Supabase
        filters = {}
        if date_from:
            filters['date_from'] = date_from_obj.isoformat()
        if date_to:
            filters['date_to'] = date_to_obj.isoformat()
        
        # Get all sessions from Supabase (no pagination limit for stats)
        result = supabase_service.get_sessions(
            limit=1000,  # Large limit for stats
            offset=0,
            filters=filters
        )
        
        if result.get('error'):
            logger.error(f"Supabase error in stats: {result['error']}")
            sessions = []
        else:
            sessions = result.get('sessions', [])
        
        # Calculate stats from Supabase data
        total_sessions = len(sessions)
        active_sessions = sum(1 for s in sessions if s.get('status') == 'active')
        escalated_sessions = sum(1 for s in sessions if s.get('status') == 'escalated') 
        resolved_sessions = sum(1 for s in sessions if s.get('status') == 'resolved')
        completed_sessions = sum(1 for s in sessions if s.get('completed', False))
        
        # Calculate AI engagement stats
        ai_engaged_sessions = sum(1 for s in sessions if s.get('ai_engaged', False))
        ai_not_engaged_sessions = total_sessions - ai_engaged_sessions
        
        # QA Statistics
        qa_stats = {
            'unchecked': sum(1 for s in sessions if s.get('qa_status') == 'unchecked'),
            'passed': sum(1 for s in sessions if s.get('qa_status') == 'passed'),
            'issue': sum(1 for s in sessions if s.get('qa_status') == 'issue'),
            'fixed': sum(1 for s in sessions if s.get('qa_status') == 'fixed')
        }
        
        # Get QA stats from PostgreSQL  
        qa_result = db.session.query(
            func.count(MessengerSessionQA.id).label('total_qa'),
            func.sum(case((MessengerSessionQA.qa_status == 'passed', 1), else_=0)).label('passed'),
            func.sum(case((MessengerSessionQA.qa_status == 'unchecked', 1), else_=0)).label('unchecked'),
            func.sum(case((MessengerSessionQA.qa_status.in_(['issue', 'fixed']), 1), else_=0)).label('issues')
        ).first()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_sessions': total_sessions,
                'passed': qa_result.passed or 0,
                'completed': completed_sessions,
                'unchecked': qa_result.unchecked or 0
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
        # First get the session from Supabase to get session_id string
        result = supabase_service.get_sessions(limit=1000, offset=0, filters={})
        if result.get('error'):
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve session from database'
            }), 500
            
        sessions = result.get('sessions', [])
        supabase_session = None
        for session in sessions:
            if session.get('id') == session_id:
                supabase_session = session
                break
                
        if not supabase_session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
            
        session_id_str = supabase_session.get('session_id')
        if not session_id_str:
            return jsonify({
                'status': 'error',
                'message': 'Session ID not found'
            }), 404
        
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 401
        
        # Find or create QA record in PostgreSQL
        qa_session = ChatSession.query.filter_by(session_id=session_id_str).first()
        if not qa_session:
            # Create new QA record
            qa_session = ChatSession(
                session_id=session_id_str,
                customer_name=supabase_session.get('customer_name'),
                contact_id=supabase_session.get('contact_id'),
                conversation_start=datetime.fromisoformat(supabase_session.get('conversation_start', '').replace('Z', '+00:00')),
                last_message_time=datetime.fromisoformat(supabase_session.get('last_message_time', '').replace('Z', '+00:00')),
                message_count=supabase_session.get('message_count', 0),
                status=supabase_session.get('status', 'active'),
                ai_engaged=supabase_session.get('ai_engaged', False)
            )
            db.session.add(qa_session)
        
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
        
        # Send webhook notification for QA issues
        if qa_session.qa_status == 'issue':
            try:
                import requests
                webhook_url = "https://n8n-g0cw.onrender.com/webhook/new-sweats-ticket-issue"
                webhook_payload = {
                    "session_id": qa_session.session_id,
                    "customer_name": qa_session.customer_name,
                    "contact_id": qa_session.contact_id,
                    "qa_status": qa_session.qa_status,
                    "qa_notes": qa_session.qa_notes,
                    "qa_reviewer": qa_session.qa_status_updated_by,
                    "timestamp": qa_session.qa_status_updated_at.isoformat() if qa_session.qa_status_updated_at else None
                }
                
                response = requests.post(webhook_url, json=webhook_payload, timeout=10)
                if response.status_code == 200:
                    logger.info(f"Successfully sent QA issue notification for session {session_id}")
                else:
                    logger.warning(f"Webhook notification failed with status {response.status_code} for session {session_id}")
                    
            except Exception as webhook_error:
                logger.error(f"Failed to send webhook notification for session {session_id}: {str(webhook_error)}")
                # Don't fail the main request if webhook fails
        
        logger.info(f"Updated QA for messenger session {session_id} by {current_user.username}")
        
        return jsonify({
            'status': 'success',
            'message': 'QA information updated successfully',
            'data': qa_session.to_dict()
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
    """Get daily statistics for messenger sessions"""
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Default to last 7 days if no dates provided
        if not date_from:
            date_from_obj = datetime.now(SYDNEY_TZ) - timedelta(days=7)
        else:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        
        if not date_to:
            date_to_obj = datetime.now(SYDNEY_TZ)
        else:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        
        # Get all sessions from Supabase for the date range
        result = supabase_service.get_sessions(
            limit=1000,
            offset=0,
            filters={
                'date_from': date_from_obj.isoformat(),
                'date_to': date_to_obj.isoformat()
            }
        )
        
        if result.get('error'):
            sessions = []
        else:
            sessions = result.get('sessions', [])
        
        # Group sessions by date
        daily_stats = {}
        for session in sessions:
            # Extract date from session creation
            session_date = session.get('conversation_start', '')[:10]  # YYYY-MM-DD format
            
            if session_date not in daily_stats:
                daily_stats[session_date] = {
                    'date': session_date,
                    'total': 0,
                    'active': 0,
                    'completed': 0,
                    'ai_engaged': 0
                }
            
            daily_stats[session_date]['total'] += 1
            
            if session.get('status') == 'active':
                daily_stats[session_date]['active'] += 1
            
            if session.get('completed', False):
                daily_stats[session_date]['completed'] += 1
                
            if session.get('ai_engaged', False):
                daily_stats[session_date]['ai_engaged'] += 1
        
        # Convert to list and sort by date
        stats_list = sorted(daily_stats.values(), key=lambda x: x['date'])
        
        return jsonify({
            'status': 'success',
            'data': stats_list
        })
        
    except Exception as e:
        logger.error(f"Error getting daily messenger session stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get daily statistics',
            'error': str(e)
        }), 500