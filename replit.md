# Web Chat Landing Page AI Lead Generation Dashboard

## Overview
This Flask-based web application manages web chat sessions from landing pages and provides a dashboard for monitoring AI agent interactions with potential leads. Its core purpose is to streamline lead generation through AI-powered conversations, enhance conversion rates, and provide comprehensive analytics of web-based customer interactions. Key capabilities include an embeddable chat widget for lead generation, storage of chat transcripts, and quality assurance features for team oversight. The project aims to improve lead acquisition and management efficiency for businesses.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- Frontend Framework: Vanilla JavaScript with Bootstrap 5.3 for responsive design.
- Data Visualization: Chart.js for graphical representation of metrics.
- Iconography: Font Awesome for consistent UI elements.
- Theming: Supports both dark and light themes.
- Chat UI: Custom responsive chat interface with message bubbles and typing indicators.

### Technical Implementations
- Backend Framework: Flask 3.1+ with SQLAlchemy ORM.
- Database: PostgreSQL 16 for robust data storage.
- API: RESTful endpoints with JSON for data exchange.
- Authentication: Session-based authentication with secure password hashing.
- Deployment: Gunicorn WSGI server, optimized for Replit auto-scaling.
- Data Persistence: Browser sessions and localStorage for frontend state management.

### Feature Specifications
- **Web Chat Session Management**: Tracks web-based chat conversations, including session metadata, AI engagement, lead data collection, and QA fields.
- **Embeddable Chat Widget**: A standalone, embeddable chat interface for WordPress sites, designed for AI-initiated conversations and real-time communication with the backend.
- **Lead Data Collection**: Captures visitor information and stores complete chat transcripts, with refactored database architecture for dedicated lead information (`leads` table).
- **Webhook Integration**: Sends completed lead data to external automation workflows (e.g., N8n) upon session completion.
- **User Management**: Handles user authentication, role-based access (admin/agent), and session control.
- **Error Logging**: Captures and logs automation workflow errors.
- **API Endpoints**: Comprehensive RESTful APIs for managing web chat sessions, QA updates, statistics, error logging, secure conversation retrieval, and providing contextual conversation history (excluding the most recent AI message).
- **Quality Assurance System**: Implements a four-state QA workflow (unchecked → passed/issue → fixed) with user attribution and developer feedback.
- **Data Flow**: Sessions are created via web chat widget, processed by AI agent, lead data sent to webhook, displayed on dashboard, and reviewed via QA system.
- **Completion Status Sync**: Robust system to automatically detect and update session completion status, ensuring consistency across dashboard and session details.
- **Export Functionality**: Allows export of complete chat sessions, including lead information, conversation threads, and QA notes.

### System Design Choices
- **Unified Data Storage**: Consolidated all data storage to PostgreSQL.
- **Independent Status Management**: Implemented a dual status system (`completion_status` and `archive_status`) for granular control over session visibility and progress.
- **Real-time Updates**: Designed for immediate UI updates for operations like archiving, deleting, and session additions.
- **Modular Design**: Separation of concerns between backend (Flask, SQLAlchemy) and frontend (Vanilla JS, Bootstrap).
- **Auto-Sync System**: Implemented comprehensive auto-sync mechanisms to prevent orphaned sessions, including smart auto-detection, background processing, and a manual sync endpoint.
- **AI-Initiated Conversations**: The chat widget is designed for the AI to send the first message, starting the conversation.

## External Dependencies

### Required Services
- **PostgreSQL**: Main relational database.
- **Facebook Messenger**: Source platform for customer conversational data.
- **Resend Email API**: Used for sending automated QA issue notifications and other email alerts.
- **N8n**: Automation platform for webhook processing, specifically for integrating with CRM systems like Monday.com.

### Python Libraries
- `Flask`, `Flask-SQLAlchemy`, `Flask-CORS`
- `psycopg2-binary`, `SQLAlchemy`
- `Marshmallow`, `email-validator`
- `requests`, `Werkzeug`
- `pytz`

### Frontend Libraries
- `Bootstrap 5.3`
- `Chart.js`
- `Font Awesome 6.0`
- `BotUI` (Note: Replaced by custom UI for embeddable chat, but might be used elsewhere)