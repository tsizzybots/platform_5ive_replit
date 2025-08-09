from datetime import datetime
from app import db
from sqlalchemy import Index
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin', 'agent', 'qa', 'qa_dev'
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

class Lead(db.Model):
    """Model for storing lead information separately from chat sessions"""
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    
    # Lead information fields
    full_name = db.Column(db.String(255), nullable=True)
    company_name = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)
    ai_interest_reason = db.Column(db.Text, nullable=True)
    ai_implementation_known = db.Column(db.Text, nullable=True)
    business_challenges = db.Column(db.Text, nullable=True)
    business_goals_6_12m = db.Column(db.Text, nullable=True)
    ai_budget_allocated = db.Column(db.Text, nullable=True)
    ai_implementation_timeline = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_lead_session_id', 'session_id'),
        Index('idx_lead_email', 'email'),
        Index('idx_lead_created', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'full_name': self.full_name,
            'company_name': self.company_name,
            'email': self.email,
            'phone_number': self.phone_number,
            'ai_interest_reason': self.ai_interest_reason,
            'ai_implementation_known': self.ai_implementation_known,
            'business_challenges': self.business_challenges,
            'business_goals_6_12m': self.business_goals_6_12m,
            'ai_budget_allocated': self.ai_budget_allocated,
            'ai_implementation_timeline': self.ai_implementation_timeline,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Lead {self.id}: {self.full_name} - {self.email}>'


class MessengerSession(db.Model):
    """Model for chat sessions stored in PostgreSQL - supports both messenger and web chat"""
    __tablename__ = 'messenger_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    conversation_start = db.Column(db.DateTime, nullable=False)
    last_message_time = db.Column(db.DateTime, nullable=False)
    message_count = db.Column(db.Integer, nullable=False, default=1)
    session_summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='active')
    completion_status = db.Column(db.String(50), nullable=False, default='incomplete')
    ai_engaged = db.Column(db.Boolean, nullable=False, default=False)
    ai_response = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Session source tracking (messenger, web_chat)
    session_source = db.Column(db.String(50), nullable=False, default='messenger')
    
    # Webhook tracking
    webhook_delivered = db.Column(db.Boolean, nullable=False, default=False)
    webhook_delivery_at = db.Column(db.DateTime, nullable=True)
    webhook_url = db.Column(db.String(500), nullable=True)
    webhook_response = db.Column(db.Text, nullable=True)
    
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
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_session_source', 'session_source'),
        Index('idx_session_status', 'status'),
        Index('idx_session_completion', 'completion_status'),
        Index('idx_session_created', 'created_at'),
        Index('idx_session_qa_status', 'qa_status'),
        Index('idx_webhook_delivered', 'webhook_delivered'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'conversation_start': self.conversation_start.isoformat() if self.conversation_start else None,
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'message_count': self.message_count,
            'session_summary': self.session_summary,
            'status': self.status,
            'completion_status': self.completion_status,
            'ai_engaged': self.ai_engaged,
            'ai_response': self.ai_response,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'session_source': self.session_source,
            'webhook_delivered': self.webhook_delivered,
            'webhook_delivery_at': self.webhook_delivery_at.isoformat() if self.webhook_delivery_at else None,
            'webhook_url': self.webhook_url,
            'webhook_response': self.webhook_response,
            'qa_status': self.qa_status,
            'qa_status_updated_by': self.qa_status_updated_by,
            'qa_status_updated_at': self.qa_status_updated_at.isoformat() if self.qa_status_updated_at else None,
            'qa_notes': self.qa_notes,
            'qa_notes_updated_at': self.qa_notes_updated_at.isoformat() if self.qa_notes_updated_at else None,
            'dev_feedback': self.dev_feedback,
            'dev_feedback_by': self.dev_feedback_by,
            'dev_feedback_at': self.dev_feedback_at.isoformat() if self.dev_feedback_at else None
        }
    
    def __repr__(self):
        return f'<MessengerSession {self.session_id}: {self.session_source} - {self.completion_status}>'



class ChatSessionForDashboard(db.Model):
    """Model for individual chat messages/interactions stored in PostgreSQL"""
    __tablename__ = 'chat_sessions_for_dashboard'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, nullable=False)
    dateTime = db.Column(db.DateTime(timezone=True), nullable=True, default=db.func.now())
    userAi = db.Column(db.String, nullable=True)  # 'human' or 'ai'
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
            'dateTime': self.dateTime.isoformat() if self.dateTime else None,
            'userAi': self.userAi,
            'messageStr': self.messageStr
        }
    
    def __repr__(self):
        return f'<ChatSessionForDashboard {self.session_id}: {self.userAi}>'
