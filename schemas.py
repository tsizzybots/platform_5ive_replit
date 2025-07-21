from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime

class EmailInquirySchema(Schema):
    id = fields.Integer(dump_only=True)
    ticket_id = fields.String(required=True, validate=validate.Length(min=1, max=100))
    subject = fields.String(required=True, validate=validate.Length(min=0, max=1000))
    body = fields.String(required=True, validate=validate.Length(min=1))
    sender_email = fields.Email(required=True)
    sender_name = fields.String(allow_none=True, validate=validate.Length(max=255))
    received_date = fields.DateTime(required=True)
    inquiry_type = fields.String(allow_none=True, validate=validate.Length(max=100))
    ticket_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    status = fields.String(load_default='skipped')
    engaged = fields.Boolean(load_default=False)
    ai_response = fields.String(allow_none=True)
    archived = fields.Boolean(dump_only=True)
    archived_at = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # QA Fields
    qa_status = fields.String(validate=validate.OneOf(['unchecked', 'passed', 'issue', 'fixed']), load_default='unchecked')
    qa_status_updated_by = fields.String(allow_none=True)
    qa_status_updated_at = fields.DateTime(dump_only=True)
    qa_notes = fields.String(allow_none=True)
    qa_notes_updated_at = fields.DateTime(dump_only=True)
    
    # Developer Feedback Fields
    dev_feedback = fields.String(allow_none=True)
    dev_feedback_by = fields.String(allow_none=True)
    dev_feedback_at = fields.DateTime(dump_only=True)

class EmailInquiryUpdateSchema(Schema):
    status = fields.String()
    engaged = fields.Boolean()
    ai_response = fields.String(allow_none=True)
    
    # QA Fields
    qa_status = fields.String(validate=validate.OneOf(['unchecked', 'passed', 'issue', 'fixed']))
    qa_status_updated_by = fields.String(allow_none=True)
    qa_notes = fields.String(allow_none=True)
    
    # Developer Feedback Fields
    dev_feedback = fields.String(allow_none=True)
    dev_feedback_by = fields.String(allow_none=True)

class EmailInquiryQuerySchema(Schema):
    status = fields.String()
    engaged = fields.Boolean()
    sender_email = fields.String()
    ticket_id = fields.String()
    inquiry_type = fields.String()
    date_from = fields.DateTime()
    date_to = fields.DateTime()
    qa_status = fields.String(validate=validate.OneOf(['unchecked', 'passed', 'issue', 'fixed']))
    page = fields.Integer(validate=validate.Range(min=1), load_default=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), load_default=20)

class ErrorSchema(Schema):
    id = fields.Integer(dump_only=True)
    timestamp = fields.DateTime(required=True)
    workflow = fields.String(required=True, validate=validate.Length(min=1, max=255))
    url = fields.String(allow_none=True, validate=validate.Length(max=500))
    node = fields.String(allow_none=True, validate=validate.Length(max=255))
    error_message = fields.String(required=True, validate=validate.Length(min=1))
    created_at = fields.DateTime(dump_only=True)

class ErrorQuerySchema(Schema):
    workflow = fields.String()
    date_from = fields.DateTime()
    date_to = fields.DateTime()
    page = fields.Integer(validate=validate.Range(min=1), load_default=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), load_default=20)

class MessengerSessionSchema(Schema):
    id = fields.Integer(dump_only=True)
    session_id = fields.String(required=True, validate=validate.Length(min=1, max=100))
    customer_name = fields.String(allow_none=True, validate=validate.Length(max=255))
    customer_id = fields.String(allow_none=True, validate=validate.Length(max=255))
    conversation_start = fields.DateTime(required=True)
    last_message_time = fields.DateTime(required=True)
    message_count = fields.Integer(load_default=1, validate=validate.Range(min=1))
    session_summary = fields.String(allow_none=True)
    status = fields.String(load_default='active', validate=validate.OneOf(['active', 'resolved', 'escalated']))
    ai_engaged = fields.Boolean(load_default=False)
    ai_response = fields.String(allow_none=True)
    archived = fields.Boolean(dump_only=True)
    archived_at = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # QA Fields
    qa_status = fields.String(validate=validate.OneOf(['unchecked', 'passed', 'issue', 'fixed']), load_default='unchecked')
    qa_status_updated_by = fields.String(allow_none=True)
    qa_status_updated_at = fields.DateTime(dump_only=True)
    qa_notes = fields.String(allow_none=True)
    qa_notes_updated_at = fields.DateTime(dump_only=True)
    
    # Developer Feedback Fields
    dev_feedback = fields.String(allow_none=True)
    dev_feedback_by = fields.String(allow_none=True)
    dev_feedback_at = fields.DateTime(dump_only=True)

class MessengerSessionUpdateSchema(Schema):
    status = fields.String(validate=validate.OneOf(['active', 'resolved', 'escalated']))
    ai_engaged = fields.Boolean()
    ai_response = fields.String(allow_none=True)
    session_summary = fields.String(allow_none=True)
    message_count = fields.Integer(validate=validate.Range(min=1))
    last_message_time = fields.DateTime()
    
    # QA Fields
    qa_status = fields.String(validate=validate.OneOf(['unchecked', 'passed', 'issue', 'fixed']))
    qa_status_updated_by = fields.String(allow_none=True)
    qa_notes = fields.String(allow_none=True)
    
    # Developer Feedback Fields
    dev_feedback = fields.String(allow_none=True)
    dev_feedback_by = fields.String(allow_none=True)

class MessengerSessionQuerySchema(Schema):
    status = fields.String(validate=validate.OneOf(['active', 'resolved', 'escalated']))
    ai_engaged = fields.Boolean()
    customer_id = fields.String()
    session_id = fields.String()
    date_from = fields.DateTime()
    date_to = fields.DateTime()
    qa_status = fields.String(validate=validate.OneOf(['unchecked', 'passed', 'issue', 'fixed']))
    page = fields.Integer(validate=validate.Range(min=1), load_default=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), load_default=20)

# Schema instances
email_inquiry_schema = EmailInquirySchema()
email_inquiry_update_schema = EmailInquiryUpdateSchema()
email_inquiry_query_schema = EmailInquiryQuerySchema()
error_schema = ErrorSchema()
error_query_schema = ErrorQuerySchema()
messenger_session_schema = MessengerSessionSchema()
messenger_session_update_schema = MessengerSessionUpdateSchema()
messenger_session_query_schema = MessengerSessionQuerySchema()
