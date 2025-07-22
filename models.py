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

class MessengerSession(db.Model):
    """Model for messenger sessions stored in PostgreSQL"""
    __tablename__ = 'messenger_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    customer_name = db.Column(db.String(255), nullable=True)
    customer_id = db.Column(db.String(255), nullable=True)
    conversation_start = db.Column(db.DateTime, nullable=False)
    last_message_time = db.Column(db.DateTime, nullable=False)
    message_count = db.Column(db.Integer, nullable=False, default=1)
    session_summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='active')
    ai_engaged = db.Column(db.Boolean, nullable=False, default=False)
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

class MessengerSessionQA(db.Model):
    """Model for storing QA information for messenger sessions in PostgreSQL"""
    __tablename__ = 'messenger_session_qa'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, unique=True)  # Links to Supabase session
    qa_status = db.Column(db.String(50), nullable=False, default='unchecked')  # unchecked, passed, issue, fixed
    qa_status_updated_by = db.Column(db.String(255), nullable=True)
    qa_status_updated_at = db.Column(db.DateTime, nullable=True)
    qa_notes = db.Column(db.Text, nullable=True)
    qa_notes_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Developer Feedback
    dev_feedback = db.Column(db.Text, nullable=True)
    dev_feedback_by = db.Column(db.String(255), nullable=True)
    dev_feedback_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add indexes for frequently queried fields
    __table_args__ = (
        Index('idx_qa_session_id', 'session_id'),
        Index('idx_qa_status', 'qa_status'),
        Index('idx_qa_updated_at', 'qa_status_updated_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'qa_status': self.qa_status,
            'qa_status_updated_by': self.qa_status_updated_by,
            'qa_status_updated_at': self.qa_status_updated_at.isoformat() if self.qa_status_updated_at else None,
            'qa_notes': self.qa_notes,
            'qa_notes_updated_at': self.qa_notes_updated_at.isoformat() if self.qa_notes_updated_at else None,
            'dev_feedback': self.dev_feedback,
            'dev_feedback_by': self.dev_feedback_by,
            'dev_feedback_at': self.dev_feedback_at.isoformat() if self.dev_feedback_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<MessengerSessionQA {self.session_id}: {self.qa_status}>'

class ChatSessionForDashboard(db.Model):
    """Model for individual chat messages/interactions stored in PostgreSQL"""
    __tablename__ = 'chat_sessions_for_dashboard'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, nullable=False)
    firstName = db.Column(db.String, nullable=True)
    lastName = db.Column(db.String, nullable=True)
    contactID = db.Column(db.String, nullable=True)
    dateTime = db.Column(db.DateTime(timezone=True), nullable=True, default=db.func.now())
    userAi = db.Column(db.String, nullable=True)  # 'user' or 'ai'
    messageStr = db.Column(db.String, nullable=True)
    
    # Add indexes for frequently queried fields
    __table_args__ = (
        Index('idx_chat_session_id', 'session_id'),
        Index('idx_chat_datetime', 'dateTime'),
        Index('idx_chat_user_ai', 'userAi'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'firstName': self.firstName,
            'lastName': self.lastName,
            'contactID': self.contactID,
            'dateTime': self.dateTime.isoformat() if self.dateTime else None,
            'userAi': self.userAi,
            'messageStr': self.messageStr
        }
    
    def __repr__(self):
        return f'<ChatSessionForDashboard {self.session_id}: {self.userAi}>'
