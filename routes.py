from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import Error, User, ChatSession
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
    """Get a specific messenger session by ID"""
    try:
        session_obj = ChatSession.query.get(session_id)
        if not session_obj:
            return jsonify({
                'status': 'error',
                'message': 'Messenger session not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': chat_session_schema.dump(session_obj)
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
        
        return jsonify({
            'status': 'success',
            'data': {
                'totals': {
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'escalated_sessions': escalated_sessions,
                    'resolved_sessions': resolved_sessions
                },
                'ai_engagement': {
                    'ai_engaged': ai_engaged_sessions,
                    'ai_not_engaged': ai_not_engaged_sessions,
                    'engagement_rate': round((ai_engaged_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2)
                },
                'qa_stats': qa_stats,
                'date_range': {
                    'from': date_from_obj.isoformat(),
                    'to': date_to_obj.isoformat()
                }
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
        session_obj = ChatSession.query.get(session_id)
        if not session_obj:
            return jsonify({
                'status': 'error',
                'message': 'Messenger session not found'
            }), 404
        
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 401
        
        data = request.json
        sydney_now = get_sydney_time()
        
        # Update QA status if provided
        if 'qa_status' in data:
            session_obj.qa_status = data['qa_status']
            session_obj.qa_status_updated_by = current_user.username
            session_obj.qa_status_updated_at = sydney_now
        
        # Update QA notes if provided
        if 'qa_notes' in data:
            session_obj.qa_notes = data['qa_notes']
            session_obj.qa_notes_updated_at = sydney_now
        
        # Update developer feedback if provided
        if 'dev_feedback' in data:
            session_obj.dev_feedback = data['dev_feedback']
            session_obj.dev_feedback_by = current_user.username
            session_obj.dev_feedback_at = sydney_now
        
        session_obj.updated_at = sydney_now
        db.session.commit()
        
        logger.info(f"Updated QA for messenger session {session_obj.id} by {current_user.username}")
        
        return jsonify({
            'status': 'success',
            'message': 'QA information updated successfully',
            'data': chat_session_schema.dump(session_obj)
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