# Web Chat Landing Page AI Lead Generation Dashboard

## Overview
This Flask-based web application manages web chat sessions from landing pages and provides a dashboard for monitoring AI agent interactions with potential leads. The system features an embeddable chat widget for lead generation, stores chat transcripts, and offers quality assurance capabilities for team oversight. Its core purpose is to streamline lead generation through AI-powered conversations, enhance conversion rates, and provide comprehensive analytics of web-based customer interactions.

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
- **Web Chat Session Management**: Tracks web-based chat conversations from landing pages, including session metadata, AI engagement, lead data collection, and QA fields.
- **Embeddable Chat Widget**: BotUI-powered chat interface that can be embedded in WordPress sites via iframe for lead generation.
- **Lead Data Collection**: Captures visitor information (name, email) with validation and stores complete chat transcripts.
- **Webhook Integration**: Sends completed lead data to N8n automation workflows for further processing.
- **User Management**: Handles user authentication, role-based access (admin/agent), and session control.
- **Error Logging**: Captures and logs automation workflow errors.
- **API Endpoints**: Comprehensive set of RESTful APIs for managing web chat sessions, QA updates, statistics, error logging, and secure conversation retrieval.
- **Quality Assurance System**: Implements a four-state QA workflow (unchecked → passed/issue → fixed) with user attribution and developer feedback.
- **Data Flow**: Sessions are created via web chat widget, processed by AI agent, lead data sent to webhook, displayed on dashboard, and reviewed via QA system.

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
- **Current Active Tables**: 5 essential tables provide complete functionality:
  - `chat_sessions_for_dashboard`: Individual chat messages/interactions 
  - `messenger_sessions`: Session metadata with integrated QA functionality
  - `leads`: Dedicated lead qualification and contact information (NEW)
  - `users`: User authentication and role management
  - `errors`: Error logging for automation workflows
- **Lead Data Architecture**: Lead information is now properly separated into dedicated `leads` table with foreign key relationship to `messenger_sessions` via `session_id` for better data integrity and query performance

## Changelog
- August 9, 2025: **CONVERSATION API ENDPOINT** - Added secure API endpoint for external conversation retrieval
  - **NEW ENDPOINT**: `/api/conversation/<session_id>` with API key authentication using CONVERSATION_API_KEY
  - **STREAMLINED RESPONSE**: Returns clean conversation data with chronologically ordered messages (most recent at bottom)
  - **SECURITY**: Implements API key validation via X-API-Key or Authorization headers (Bearer token support)
  - **ERROR HANDLING**: Proper HTTP status codes and error messages for authentication, validation, and not found scenarios
  - **MESSAGE ORDERING**: Conversations ordered chronologically with most recent messages at the bottom as requested
- August 10, 2025: **LEAD UPSERT API ENDPOINT** - Added intelligent lead data management endpoint
  - **NEW ENDPOINT**: `/api/lead/<session_id>` for creating and updating lead information
  - **SECURITY**: Uses same CONVERSATION_API_KEY authentication as conversation endpoint (X-API-Key or Authorization Bearer)
  - **SMART UPSERT**: Automatically detects if session exists and creates new record or updates existing one
  - **PARTIAL UPDATES**: Supports updating individual fields without affecting other data
  - **COMPREHENSIVE FIELDS**: Handles all lead qualification fields (contact info, AI interest data, business goals)
  - **DETAILED RESPONSES**: Returns action taken (created/updated), affected fields, and lead ID for tracking
- August 10, 2025: **DELETION SYSTEM FIX** - Enhanced session deletion to properly handle testing and web chat sessions
  - **IMPROVED CRITERIA**: Now properly identifies testing sessions including 'Web Chat User', sessions with 'test'/'realtime'/'verification' patterns
  - **COMPLETE DELETION**: Ensures both chat_sessions_for_dashboard messages and leads table records are removed
  - **ENHANCED PATTERNS**: Supports sessions starting with 'test_' or 'session_' and web_chat source sessions
- August 9, 2025: **LEAD DATA SEPARATION** - Successfully refactored database architecture to separate lead information from session management
  - **NEW LEAD TABLE**: Created dedicated `leads` table with comprehensive lead qualification fields (full_name, company_name, email, phone_number, AI interest data)
  - **DATA MIGRATION**: Migrated 6 existing lead records from messenger_sessions to new leads table structure
  - **API REFACTORING**: Updated all API endpoints to integrate with separated Lead model while maintaining frontend compatibility
  - **SESSION CLEANUP**: Removed lead-related fields from MessengerSession model for cleaner data separation
  - **IMPROVED ARCHITECTURE**: Enhanced data integrity with proper foreign key relationships and dedicated lead management
- August 9, 2025: **COMPLETION LOGIC UPDATE** - Updated conversation completion detection from "https://shorturl.at/9u9oh" to "within 24 hours" phrase matching
- August 9, 2025: **WEBHOOK URL UPDATE** - Updated test AI webhook to new N8n endpoint: `https://n8n-g0cw.onrender.com/webhook/44e68b37-d078-44b3-b3bc-2a51a9822aca`
- August 9, 2025: **DATABASE STRUCTURE UPDATE** - Updated chat_sessions_for_dashboard table structure to simplified format (removed firstName, lastName, contactID fields), updated all models and API endpoints accordingly
- August 8, 2025: **DEPLOYMENT OPTIMIZATION** - Applied comprehensive deployment fixes for production readiness
  - **HEALTH CHECK ENDPOINT**: Added `/health` endpoint for deployment service verification with database connectivity testing
  - **ROOT STATUS ENDPOINT**: Added `/` endpoint providing API status and basic information
  - **ERROR HANDLING**: Enhanced app initialization with comprehensive error handling and graceful failure modes
  - **DATABASE CONNECTION**: Fixed SQL query warnings using SQLAlchemy text() for proper query execution
  - **ENVIRONMENT VARIABLES**: Added proper environment variable validation and logging for deployment scenarios
  - **LOGGING IMPROVEMENTS**: Enhanced logging configuration for production debugging and monitoring
  - **GUNICORN COMPATIBILITY**: Ensured proper Flask app initialization for Gunicorn WSGI server deployment
- August 8, 2025: **POSTGRESQL DATABASE INTEGRATION** - Successfully connected PostgreSQL database using Neon
  - **DATABASE STATUS**: PostgreSQL database fully operational with auto-created tables
  - **VERIFIED TABLES**: All 4 required tables (users, messenger_sessions, chat_sessions_for_dashboard, errors) created successfully
  - **CONNECTION VERIFIED**: Database queries working properly with environment variables configured
  - **APPLICATION STATUS**: Flask application running on port 5000 with full database connectivity
- August 5, 2025: **DATABASE CLEANUP** - Removed unused database tables for cleaner architecture
  - **REMOVED REDUNDANT TABLE**: Deleted `messenger_session_qa` table (0 records, functionality moved to `messenger_sessions`)
  - **REMOVED LEGACY TABLE**: Deleted `n8n_chat_histories_mixandmatch_demo` table (legacy data, not referenced in code)
  - **QA FUNCTIONALITY**: All QA features (qa_status, qa_notes, dev_feedback) integrated into main `messenger_sessions` table
  - **VERIFIED SAFETY**: 100% confirmed tables were unused before removal through code analysis and data verification
- August 5, 2025: **AI CHAT SESSION EXPORT FEATURE** - Added comprehensive session export functionality for IzzyDev users