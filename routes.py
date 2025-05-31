from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import EmailInquiry
from schemas import email_inquiry_schema, email_inquiry_update_schema, email_inquiry_query_schema
from marshmallow import ValidationError
from sqlalchemy import and_, or_
from datetime import datetime
import logging
import os
from functools import wraps

logger = logging.getLogger(__name__)

# Hardcoded login credentials
ADMIN_USERNAME = "sweatsADMIN"
ADMIN_PASSWORD = "ctp4kbk8HGW5emb!yze"

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# API Key Authentication
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_api_key = os.environ.get('API_KEY')
        
        if not expected_api_key:
            # If no API key is set, allow access (for development)
            return f(*args, **kwargs)
            
        if not api_key or api_key != expected_api_key:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or missing API key'
            }), 401
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login page and authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle logout"""
    session.pop('logged_in', None)
    flash('Successfully logged out!', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Render the main interface for testing the API"""
    return render_template('index.html')

@app.route('/api/inquiries', methods=['POST'])
@require_api_key
def create_inquiry():
    """Create a new email inquiry"""
    try:
        # Validate input data
        data = email_inquiry_schema.load(request.json)
        
        # Create new inquiry
        inquiry = EmailInquiry(**data)
        db.session.add(inquiry)
        db.session.commit()
        
        logger.info(f"Created new inquiry: {inquiry.id}")
        return jsonify({
            'status': 'success',
            'message': 'Email inquiry created successfully',
            'data': email_inquiry_schema.dump(inquiry)
        }), 201
        
    except ValidationError as e:
        logger.error(f"Validation error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        logger.error(f"Error creating inquiry: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to create email inquiry',
            'error': str(e)
        }), 500

@app.route('/api/inquiries/<int:inquiry_id>', methods=['GET'])
def get_inquiry(inquiry_id):
    """Get a specific email inquiry by ID"""
    try:
        inquiry = EmailInquiry.query.get(inquiry_id)
        if not inquiry:
            return jsonify({
                'status': 'error',
                'message': 'Email inquiry not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': email_inquiry_schema.dump(inquiry)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving inquiry {inquiry_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve email inquiry',
            'error': str(e)
        }), 500

@app.route('/api/inquiries/<int:inquiry_id>', methods=['PUT'])
@require_api_key
def update_inquiry(inquiry_id):
    """Update an email inquiry (status, engagement, AI response)"""
    try:
        inquiry = EmailInquiry.query.get(inquiry_id)
        if not inquiry:
            return jsonify({
                'status': 'error',
                'message': 'Email inquiry not found'
            }), 404
            
        # Validate update data
        data = email_inquiry_update_schema.load(request.json)
        
        # Update fields
        for key, value in data.items():
            setattr(inquiry, key, value)
        
        inquiry.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Updated inquiry: {inquiry.id}")
        return jsonify({
            'status': 'success',
            'message': 'Email inquiry updated successfully',
            'data': email_inquiry_schema.dump(inquiry)
        })
        
    except ValidationError as e:
        logger.error(f"Validation error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        logger.error(f"Error updating inquiry {inquiry_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to update email inquiry',
            'error': str(e)
        }), 500

@app.route('/api/inquiries', methods=['GET'])
def list_inquiries():
    """List email inquiries with optional filtering and pagination"""
    try:
        # Validate query parameters
        query_params = email_inquiry_query_schema.load(request.args)
        
        # Build query
        query = EmailInquiry.query
        
        # Apply filters
        if 'status' in query_params:
            query = query.filter(EmailInquiry.status == query_params['status'])
        
        if 'engaged' in query_params:
            query = query.filter(EmailInquiry.engaged == query_params['engaged'])
            
        if 'sender_email' in query_params:
            query = query.filter(EmailInquiry.sender_email == query_params['sender_email'])
            
        if 'ticket_id' in query_params:
            query = query.filter(EmailInquiry.ticket_id == query_params['ticket_id'])
            
        if 'date_from' in query_params:
            query = query.filter(EmailInquiry.received_date >= query_params['date_from'])
            
        if 'date_to' in query_params:
            query = query.filter(EmailInquiry.received_date <= query_params['date_to'])
        
        # Apply pagination
        page = query_params.get('page', 1)
        per_page = query_params.get('per_page', 20)
        
        # Order by most recent first
        query = query.order_by(EmailInquiry.created_at.desc())
        
        # Execute paginated query
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': email_inquiry_schema.dump(paginated.items, many=True),
            'pagination': {
                'page': paginated.page,
                'per_page': paginated.per_page,
                'total': paginated.total,
                'pages': paginated.pages,
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
        logger.error(f"Error listing inquiries: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve email inquiries',
            'error': str(e)
        }), 500

@app.route('/api/inquiries/stats', methods=['GET'])
def get_stats():
    """Get statistics about email inquiries"""
    try:
        total_inquiries = EmailInquiry.query.count()
        engaged_inquiries = EmailInquiry.query.filter(EmailInquiry.engaged == True).count()
        pending_inquiries = EmailInquiry.query.filter(EmailInquiry.status == 'pending').count()
        processed_inquiries = EmailInquiry.query.filter(EmailInquiry.status == 'processed').count()
        ignored_inquiries = EmailInquiry.query.filter(EmailInquiry.status == 'ignored').count()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_inquiries': total_inquiries,
                'engaged_inquiries': engaged_inquiries,
                'pending_inquiries': pending_inquiries,
                'processed_inquiries': processed_inquiries,
                'ignored_inquiries': ignored_inquiries,
                'engagement_rate': round((engaged_inquiries / total_inquiries * 100), 2) if total_inquiries > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve statistics',
            'error': str(e)
        }), 500

@app.route('/api/inquiries/<int:inquiry_id>', methods=['DELETE'])
def delete_inquiry(inquiry_id):
    """Delete an email inquiry"""
    try:
        inquiry = EmailInquiry.query.get(inquiry_id)
        if not inquiry:
            return jsonify({
                'status': 'error',
                'message': 'Email inquiry not found'
            }), 404
            
        db.session.delete(inquiry)
        db.session.commit()
        
        logger.info(f"Deleted inquiry: {inquiry_id}")
        return jsonify({
            'status': 'success',
            'message': 'Email inquiry deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting inquiry {inquiry_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete email inquiry',
            'error': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500
