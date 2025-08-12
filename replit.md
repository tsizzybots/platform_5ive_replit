# Web Chat Landing Page AI Lead Generation Dashboard

## Overview
This Flask-based web application manages web chat sessions from landing pages and provides a dashboard for monitoring AI agent interactions with potential leads. Its core purpose is to streamline lead generation through AI-powered conversations, enhance conversion rates, and provide comprehensive analytics of web-based customer interactions. Key capabilities include an embeddable chat widget for lead generation, storage of chat transcripts, and quality assurance features for team oversight.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- Frontend Framework: Vanilla JavaScript with Bootstrap 5.3 for responsive design.
- Data Visualization: Chart.js for graphical representation of metrics.
- Iconography: Font Awesome for consistent UI elements.
- Theming: Supports both dark and light themes.

### Technical Implementations
- Backend Framework: Flask 3.1+ with SQLAlchemy ORM.
- Database: PostgreSQL 16 for robust data storage.
- API: RESTful endpoints with JSON for data exchange.
- Authentication: Session-based authentication with secure password hashing.
- Deployment: Gunicorn WSGI server for production, optimized for Replit auto-scaling.
- Data Persistence: Browser sessions and localStorage for frontend state management.

### Feature Specifications
- **Web Chat Session Management**: Tracks web-based chat conversations, including session metadata, AI engagement, lead data collection, and QA fields.
- **Embeddable Chat Widget**: BotUI-powered chat interface embeddable in WordPress sites via iframe.
- **Lead Data Collection**: Captures visitor information and stores complete chat transcripts.
- **Webhook Integration**: Sends completed lead data to N8n automation workflows.
- **User Management**: Handles user authentication, role-based access (admin/agent), and session control.
- **Error Logging**: Captures and logs automation workflow errors.
- **API Endpoints**: Comprehensive RESTful APIs for managing web chat sessions, QA updates, statistics, error logging, and secure conversation retrieval, including contextual conversation history for AI agents.
- **Quality Assurance System**: Implements a four-state QA workflow (unchecked → passed/issue → fixed) with user attribution and developer feedback.
- **Data Export**: Functionality to export chat session data, including lead qualification fields and full conversation history.

### System Design Choices
- **Unified Data Storage**: Consolidated all data storage to PostgreSQL.
- **Independent Status Management**: Implemented a dual status system (`completion_status` and `archive_status`) for granular control over session visibility and progress.
- **Real-time Updates**: Designed for immediate UI updates for operations like archiving, deleting, and session additions.
- **Modular Design**: Separation of concerns between backend (Flask, SQLAlchemy) and frontend (Vanilla JS, Bootstrap).
- **Auto-Sync System**: Implemented comprehensive auto-sync mechanisms to prevent orphaned sessions, including smart auto-detection, background processing during API calls, and a manual sync endpoint.
- **Lead Data Separation**: Refactored database architecture to separate lead information into a dedicated `leads` table with foreign key relationships for improved data integrity.
- **Robust Completion Status Sync**: Ensures consistent completion status updates across the dashboard and session details, leveraging multi-layer detection and real-time UI updates.

## External Dependencies

### Required Services
- **PostgreSQL**: Main relational database.
- **Facebook Messenger**: Source platform for customer conversational data.
- **Resend Email API**: Used for sending automated QA issue notifications and other email alerts.
- **N8n**: Automation platform for webhook processing.
- **Monday.com**: For automatic lead data export and project management.

### Python Libraries
- `Flask`
- `Flask-SQLAlchemy`
- `Flask-CORS`
- `psycopg2-binary`
- `SQLAlchemy`
- `Marshmallow`
- `email-validator`
- `requests`
- `Werkzeug`
- `pytz`

### Frontend Libraries
- `Bootstrap 5.3`
- `Chart.js`
- `Font Awesome 6.0`
- `BotUI`