from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime

class EmailInquirySchema(Schema):
    id = fields.Integer(dump_only=True)
    subject = fields.String(required=True, validate=validate.Length(min=1, max=1000))
    body = fields.String(required=True, validate=validate.Length(min=1))
    sender_email = fields.Email(required=True)
    sender_name = fields.String(allow_none=True, validate=validate.Length(max=255))
    received_date = fields.DateTime(required=True)
    status = fields.String(validate=validate.OneOf(['pending', 'processed', 'ignored']), load_default='pending')
    engaged = fields.Boolean(load_default=False)
    ai_response = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class EmailInquiryUpdateSchema(Schema):
    status = fields.String(validate=validate.OneOf(['pending', 'processed', 'ignored']))
    engaged = fields.Boolean()
    ai_response = fields.String(allow_none=True)

class EmailInquiryQuerySchema(Schema):
    status = fields.String(validate=validate.OneOf(['pending', 'processed', 'ignored']))
    engaged = fields.Boolean()
    sender_email = fields.Email()
    date_from = fields.DateTime()
    date_to = fields.DateTime()
    page = fields.Integer(validate=validate.Range(min=1), load_default=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), load_default=20)

# Schema instances
email_inquiry_schema = EmailInquirySchema()
email_inquiry_update_schema = EmailInquiryUpdateSchema()
email_inquiry_query_schema = EmailInquiryQuerySchema()
