from datetime import datetime
from app import db
from sqlalchemy import Index

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
    
    # Add indexes for frequently queried fields
    __table_args__ = (
        Index('idx_ticket_id', 'ticket_id'),
        Index('idx_status', 'status'),
        Index('idx_received_date', 'received_date'),
        Index('idx_sender_email', 'sender_email'),
        Index('idx_engaged', 'engaged'),
        Index('idx_created_at', 'created_at'),
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
            'status': self.status,
            'engaged': self.engaged,
            'ai_response': self.ai_response,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<EmailInquiry {self.id}: {self.subject[:50]}...>'
