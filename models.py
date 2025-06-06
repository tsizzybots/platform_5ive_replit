from datetime import datetime
from app import db
from sqlalchemy import Index
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' or 'agent'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class EmailInquiry(db.Model):
    __tablename__ = 'email_inquiries'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(100), nullable=False, unique=True)
    subject = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(255), nullable=True)
    received_date = db.Column(db.DateTime, nullable=False)
    inquiry_type = db.Column(db.String(100), nullable=True)
    ticket_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='skipped')  # engaged, skipped
    engaged = db.Column(db.Boolean, nullable=False, default=False)
    ai_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # QA Status System
    qa_status = db.Column(db.String(50), nullable=False, default='unchecked')
    qa_status_updated_by = db.Column(db.String(255), nullable=True)
    qa_status_updated_at = db.Column(db.DateTime, nullable=True)
    qa_notes = db.Column(db.Text, nullable=True)
    qa_notes_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Developer Feedback
    dev_feedback = db.Column(db.Text, nullable=True)
    dev_feedback_by = db.Column(db.String(255), nullable=True)
    dev_feedback_at = db.Column(db.DateTime, nullable=True)
    
    # Add indexes for frequently queried fields
    __table_args__ = (
        Index('idx_ticket_id', 'ticket_id'),
        Index('idx_status', 'status'),
        Index('idx_received_date', 'received_date'),
        Index('idx_sender_email', 'sender_email'),
        Index('idx_engaged', 'engaged'),
        Index('idx_created_at', 'created_at'),
        Index('idx_qa_status', 'qa_status'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'subject': self.subject,
            'body': self.body,
            'sender_email': self.sender_email,
            'sender_name': self.sender_name,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'inquiry_type': self.inquiry_type,
            'ticket_url': self.ticket_url,
            'status': self.status,
            'engaged': self.engaged,
            'ai_response': self.ai_response,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'qa_status': self.qa_status,
            'qa_status_updated_by': self.qa_status_updated_by,
            'qa_status_updated_at': self.qa_status_updated_at.isoformat() + '+11:00' if self.qa_status_updated_at else None,
            'qa_notes': self.qa_notes,
            'qa_notes_updated_at': self.qa_notes_updated_at.isoformat() + '+11:00' if self.qa_notes_updated_at else None,
            'dev_feedback': self.dev_feedback,
            'dev_feedback_by': self.dev_feedback_by,
            'dev_feedback_at': self.dev_feedback_at.isoformat() + '+11:00' if self.dev_feedback_at else None
        }
    
    def __repr__(self):
        return f'<EmailInquiry {self.id}: {self.subject[:50]}...>'


class Error(db.Model):
    __tablename__ = 'errors'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    workflow = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=True)
    node = db.Column(db.String(255), nullable=True)
    error_message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_error_timestamp', 'timestamp'),
        Index('idx_error_workflow', 'workflow'),
        Index('idx_error_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'workflow': self.workflow,
            'url': self.url,
            'node': self.node,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Error {self.id}: {self.workflow} - {self.error_message[:50]}...>'
