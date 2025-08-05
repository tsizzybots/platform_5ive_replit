# Sweats Collective Email AI Dashboard

## Overview
This Flask-based web application manages email inquiries and provides a dashboard for monitoring AI agent interactions with customer support tickets. The system receives tickets, logs AI agent decisions, and offers quality assurance capabilities for team oversight. Its core purpose is to streamline customer support, enhance AI agent performance through continuous feedback, and provide a comprehensive overview of AI-driven customer interactions, aiming to improve efficiency and customer satisfaction.

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
- **Messenger Session Management**: Tracks Facebook Messenger conversations, including session metadata, AI engagement, and QA fields.
- **User Management**: Handles user authentication, role-based access (admin/agent), and session control.
- **Error Logging**: Captures and logs automation workflow errors.
- **API Endpoints**: Comprehensive set of RESTful APIs for managing messenger sessions, QA updates, statistics, and error logging.
- **Quality Assurance System**: Implements a four-state QA workflow (unchecked → passed/issue → fixed) with user attribution and developer feedback. Includes email integration for QA issue notifications.
- **Data Flow**: Sessions are created via Messenger bot, processed by an external AI agent, displayed on the dashboard, reviewed via QA, and issues can be escalated with developer feedback.

### System Design Choices
- **Unified Data Storage**: Consolidated all data storage to PostgreSQL for simplified architecture and enhanced CRUD operations, eliminating redundant database systems.
- **Independent Status Management**: Implemented a dual status system with `completion_status` (complete, in_progress, incomplete) separate from `archive_status` for finer control over session visibility and progress tracking.
- **Real-time Updates**: Designed for immediate UI updates for operations like archiving, deleting, and session additions, enhancing user experience.
- **Modular Design**: Separation of concerns between backend (Flask, SQLAlchemy) and frontend (Vanilla JS, Bootstrap) allows for independent development and scaling.

## External Dependencies

### Required Services
- **PostgreSQL**: Main relational database for all application data.
- **Facebook Messenger**: Source platform for customer conversational data.
- **Resend Email API**: Used for sending automated QA issue notifications and other email alerts.

### Python Libraries
- `Flask`, `Flask-SQLAlchemy`, `Flask-CORS`: Core Flask framework and extensions.
- `psycopg2-binary`, `SQLAlchemy`: PostgreSQL database driver and ORM.
- `Marshmallow`, `email-validator`: Data validation and serialization.
- `requests`, `Werkzeug`: HTTP client and utility library.
- `pytz`: Timezone handling.

### Frontend Libraries
- `Bootstrap 5.3`: CSS framework for UI styling.
- `Chart.js`: JavaScript library for data visualization.
- `Font Awesome 6.0`: Icon library.

## Database Architecture Update
- **Current Active Tables**: Only 4 essential tables remain after cleanup:
  - `chat_sessions_for_dashboard`: Individual chat messages/interactions 
  - `messenger_sessions`: Session metadata with integrated QA functionality
  - `users`: User authentication and role management
  - `errors`: Error logging for automation workflows

## Changelog
- August 5, 2025: **DATABASE CLEANUP** - Removed unused database tables for cleaner architecture
  - **REMOVED REDUNDANT TABLE**: Deleted `messenger_session_qa` table (0 records, functionality moved to `messenger_sessions`)
  - **REMOVED LEGACY TABLE**: Deleted `n8n_chat_histories_mixandmatch_demo` table (legacy data, not referenced in code)
  - **QA FUNCTIONALITY**: All QA features (qa_status, qa_notes, dev_feedback) integrated into main `messenger_sessions` table
  - **VERIFIED SAFETY**: 100% confirmed tables were unused before removal through code analysis and data verification
- August 5, 2025: **AI CHAT SESSION EXPORT FEATURE** - Added comprehensive session export functionality for IzzyDev users