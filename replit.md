# Sweats Collective Email AI Dashboard

## Overview

This is a Flask-based web application that manages email inquiries and provides a dashboard for monitoring AI agent interactions with customer support tickets. The system is designed to receive tickets from Gorgias, log AI agent decisions, and provide quality assurance capabilities for team oversight.

## System Architecture

### Backend Architecture
- **Framework**: Flask 3.1+ with SQLAlchemy ORM
- **Database**: PostgreSQL 16 with psycopg2 driver
- **API**: RESTful endpoints with JSON responses
- **Authentication**: Session-based authentication with password hashing
- **Deployment**: Gunicorn WSGI server on Replit with autoscale deployment

### Frontend Architecture
- **Framework**: Vanilla JavaScript with Bootstrap 5.3
- **UI Components**: Chart.js for data visualization, Font Awesome icons
- **Styling**: Bootstrap with custom CSS and dark/light theme support
- **State Management**: Browser sessions and localStorage for persistence

## Key Components

### Database Models
1. **EmailInquiry**: Core ticket data with AI engagement tracking
   - Ticket metadata (ID, subject, body, sender info)
   - AI decision tracking (engaged/skipped status)
   - QA system fields (qa_status, qa_notes, qa_status_updated_by)
   - Developer feedback system
   - Archival system for completed tickets

2. **User**: Authentication and role management
   - Username/password authentication with hashing
   - Role-based access (admin/agent)
   - Session management

3. **Error**: Automation error logging
   - Workflow error tracking
   - Timestamp and source identification
   - API-based error submission

### API Endpoints
- **POST /api/inquiries**: Create new tickets from Gorgias integration
- **GET /api/inquiries**: Retrieve tickets with filtering and pagination
- **PATCH /api/inquiries/{id}**: Update ticket status and QA information
- **POST /api/errors**: Log automation errors
- **Authentication endpoints**: Login/logout with session management

### Quality Assurance System
- Four-state QA workflow: unchecked → passed/issue → fixed
- User attribution for QA actions
- Developer feedback system
- Webhook integration for QA issues (sends to n8n workflow)

## Data Flow

1. **Ticket Ingestion**: Gorgias sends tickets via POST to /api/inquiries
2. **AI Processing**: External AI agent decides engagement and updates ticket status
3. **Dashboard Display**: Web interface shows tickets with filtering and statistics
4. **QA Review**: Team members review AI decisions and mark QA status
5. **Issue Escalation**: QA issues trigger webhook notifications to development team
6. **Developer Feedback**: Developers can respond to QA issues with feedback

## External Dependencies

### Required Services
- **PostgreSQL**: Primary data storage
- **Gorgias**: Source system for customer tickets
- **n8n Webhook**: QA issue notification system (https://n8n-g0cw.onrender.com/webhook/new-sweats-ticket-issue)

### Python Dependencies
- Flask ecosystem (Flask, Flask-SQLAlchemy, Flask-CORS)
- Database: psycopg2-binary, SQLAlchemy
- Validation: Marshmallow, email-validator
- HTTP: requests, Werkzeug
- Utilities: pytz (timezone handling)

### Frontend Dependencies
- Bootstrap 5.3 (CSS framework)
- Chart.js (data visualization)
- Font Awesome 6.0 (icons)

## Deployment Strategy

### Replit Configuration
- **Runtime**: Python 3.11 with PostgreSQL 16 module
- **Process**: Gunicorn with auto-scaling deployment target
- **Port Configuration**: Internal 5000 → External 80
- **Environment**: Nix package manager for system dependencies

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Flask session encryption key
- `API_KEY`: Authentication key for external API access

### Production Considerations
- Gunicorn with worker processes and port reuse
- Database connection pooling with pre-ping health checks
- Proxy fix middleware for proper request handling
- CORS enabled for API access

## Changelog
- July 16, 2025: Added "Reopen Ticket in Gorgias" functionality for archived tickets
  - New API endpoint `/api/inquiries/{id}/reopen-gorgias` to reopen tickets in Gorgias
  - Frontend button appears only for archived tickets with ticket URLs
  - Integrates with Gorgias API to change ticket status from closed to open
  - Updates local ticket status from archived back to engaged
- June 25, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.