from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import EmailInquiry, Error
from schemas import email_inquiry_schema, email_inquiry_update_schema, email_inquiry_query_schema, error_schema, error_query_schema
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
            
        if 'inquiry_type' in query_params:
            query = query.filter(EmailInquiry.inquiry_type == query_params['inquiry_type'])
            
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

@app.route('/api/inquiries/types', methods=['GET'])
def get_inquiry_types():
    """Get distinct inquiry types from the database"""
    try:
        # Query distinct inquiry types, excluding null values
        types_query = db.session.query(EmailInquiry.inquiry_type).distinct().filter(EmailInquiry.inquiry_type.isnot(None)).all()
        
        # Extract the type values and sort them
        inquiry_types = sorted([type_row[0] for type_row in types_query if type_row[0]])
        
        return jsonify({
            'status': 'success',
            'data': inquiry_types
        })
        
    except Exception as e:
        logger.error(f"Error getting inquiry types: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve inquiry types',
            'error': str(e)
        }), 500

@app.route('/api/inquiries/stats', methods=['GET'])
def get_stats():
    """Get statistics about email inquiries with optional date filtering"""
    try:
        # Parse date filters from query parameters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build base query
        query = EmailInquiry.query
        
        # Apply date filters if provided
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(EmailInquiry.received_date >= date_from_obj)
            except ValueError:
                pass  # Ignore invalid date format
                
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(EmailInquiry.received_date <= date_to_obj)
            except ValueError:
                pass  # Ignore invalid date format
        
        total_inquiries = query.count()
        engaged_inquiries = query.filter(EmailInquiry.status == 'Engaged').count()
        escalated_inquiries = query.filter(EmailInquiry.status == 'Escalated').count()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_inquiries': total_inquiries,
                'engaged_inquiries': engaged_inquiries,
                'escalated_inquiries': escalated_inquiries,
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

@app.route('/api/inquiries/daily-stats', methods=['GET'])
def get_daily_stats():
    """Get daily statistics for chart visualization"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, case
        
        # Parse date filters from query parameters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Default to current month if no dates provided
        if not date_from or not date_to:
            today = datetime.now()
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        
        # Parse dates
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        # Query daily statistics
        daily_stats = db.session.query(
            func.date(EmailInquiry.received_date).label('date'),
            func.count(EmailInquiry.id).label('total'),
            func.sum(case((EmailInquiry.status == 'Engaged', 1), else_=0)).label('engaged'),
            func.sum(case((EmailInquiry.status == 'Escalated', 1), else_=0)).label('escalated'),
            func.sum(case((EmailInquiry.status == 'Skipped', 1), else_=0)).label('skipped')
        ).filter(
            func.date(EmailInquiry.received_date) >= date_from_obj.date(),
            func.date(EmailInquiry.received_date) <= date_to_obj.date()
        ).group_by(
            func.date(EmailInquiry.received_date)
        ).order_by(
            func.date(EmailInquiry.received_date)
        ).all()
        
        # Format results
        chart_data = []
        for stat in daily_stats:
            chart_data.append({
                'date': stat.date.strftime('%Y-%m-%d'),
                'total': stat.total or 0,
                'engaged': stat.engaged or 0,
                'escalated': stat.escalated or 0,
                'skipped': stat.skipped or 0
            })
        
        return jsonify({
            'status': 'success',
            'data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error getting daily stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get daily statistics'
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

# Error logging endpoints
@app.route('/api/errors', methods=['POST'])
@require_api_key
def create_error():
    """Log a new automation error"""
    try:
        data = error_schema.load(request.json)
        
        error = Error(
            timestamp=data['timestamp'],
            workflow=data['workflow'],
            url=data.get('url'),
            node=data.get('node'),
            error_message=data['error_message']
        )
        
        db.session.add(error)
        db.session.commit()
        
        logger.info(f"New error logged: {error.workflow} - {error.error_message[:100]}...")
        return jsonify({
            'status': 'success',
            'message': 'Error logged successfully',
            'data': error_schema.dump(error)
        }), 201
        
    except ValidationError as e:
        logger.warning(f"Validation error in create_error: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error creating error log: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to log error',
            'error': str(e)
        }), 500

@app.route('/api/errors', methods=['GET'])
@login_required
def list_errors():
    """List errors with optional filtering and pagination"""
    try:
        # Parse and validate query parameters
        query_data = error_query_schema.load(request.args)
        
        # Build base query
        query = Error.query
        
        # Apply filters
        if query_data.get('workflow'):
            query = query.filter(Error.workflow.ilike(f"%{query_data['workflow']}%"))
            
        if query_data.get('date_from'):
            query = query.filter(Error.timestamp >= query_data['date_from'])
            
        if query_data.get('date_to'):
            query = query.filter(Error.timestamp <= query_data['date_to'])
        
        # Order by timestamp descending (newest first)
        query = query.order_by(Error.timestamp.desc())
        
        # Pagination
        page = query_data.get('page', 1)
        per_page = query_data.get('per_page', 20)
        
        paginated_errors = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'errors': [error_schema.dump(error) for error in paginated_errors.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated_errors.total,
                    'pages': paginated_errors.pages,
                    'has_next': paginated_errors.has_next,
                    'has_prev': paginated_errors.has_prev
                }
            }
        })
        
    except ValidationError as e:
        logger.warning(f"Validation error in list_errors: {e.messages}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error listing errors: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve errors',
            'error': str(e)
        }), 500

@app.route('/api/errors/<int:error_id>', methods=['GET'])
@login_required
def get_error(error_id):
    """Get a specific error by ID"""
    try:
        error = Error.query.get(error_id)
        if not error:
            return jsonify({
                'status': 'error',
                'message': 'Error not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': error_schema.dump(error)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving error {error_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve error',
            'error': str(e)
        }), 500

@app.route('/api/errors/<int:error_id>', methods=['DELETE'])
@login_required
def delete_error(error_id):
    """Delete an error"""
    try:
        error = Error.query.get(error_id)
        if not error:
            return jsonify({
                'status': 'error',
                'message': 'Error not found'
            }), 404
            
        db.session.delete(error)
        db.session.commit()
        
        logger.info(f"Deleted error: {error_id}")
        return jsonify({
            'status': 'success',
            'message': 'Error deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting error {error_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete error',
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
