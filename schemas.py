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
    status = fields.String(validate=validate.OneOf(['engaged', 'skipped', 'escalated', 'archived', 'Engaged', 'Skipped', 'Escalated', 'Archived']), load_default='skipped')
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
    status = fields.String(validate=validate.OneOf(['engaged', 'skipped', 'escalated', 'archived', 'Engaged', 'Skipped', 'Escalated', 'Archived']))
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
    status = fields.String(validate=validate.OneOf(['Engaged', 'Escalated', 'Skipped', 'Archived']))
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

# Schema instances
email_inquiry_schema = EmailInquirySchema()
email_inquiry_update_schema = EmailInquiryUpdateSchema()
email_inquiry_query_schema = EmailInquiryQuerySchema()
error_schema = ErrorSchema()
error_query_schema = ErrorQuerySchema()
