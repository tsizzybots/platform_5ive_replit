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
1. **MessengerSession**: Facebook Messenger session tracking
   - Session metadata (session_id, customer info, conversation timing)
   - AI engagement tracking (ai_engaged, ai_response)
   - QA system fields (qa_status, qa_notes, qa_status_updated_by)
   - Developer feedback system
   - Archival system for completed sessions

2. **User**: Authentication and role management
   - Username/password authentication with hashing
   - Role-based access (admin/agent)
   - Session management

3. **Error**: Automation error logging
   - Workflow error tracking
   - Timestamp and source identification
   - API-based error submission

### API Endpoints
- **POST /api/messenger-sessions**: Create new messenger sessions
- **GET /api/messenger-sessions**: Retrieve sessions with filtering and pagination
- **PUT /api/messenger-sessions/{id}**: Update session status and AI engagement
- **PUT /api/messenger-sessions/{id}/qa**: Update QA information for sessions
- **GET /api/messenger-sessions/stats**: Get comprehensive session statistics
- **POST /api/errors**: Log automation errors
- **Authentication endpoints**: Login/logout with session management

### Quality Assurance System
- Four-state QA workflow: unchecked → passed/issue → fixed
- User attribution for QA actions
- Developer feedback system
- Email integration for QA issues (sends via Resend API)

## Data Flow

1. **Session Creation**: Messenger bot creates sessions via POST to /api/messenger-sessions
2. **AI Processing**: External AI agent processes conversations and updates session status
3. **Dashboard Display**: Web interface shows messenger sessions with filtering and statistics
4. **QA Review**: Team members review AI decisions and mark QA status
5. **Issue Escalation**: QA issues can be tracked and managed through the interface
6. **Developer Feedback**: Developers can respond to QA issues with feedback

## External Dependencies

### Required Services
- **PostgreSQL**: Primary data storage
- **Facebook Messenger**: Source platform for customer conversations
- **Resend Email API**: QA issue notification system for automated email alerts

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
- July 22, 2025: **DELETE FUNCTION FIX** - Fixed session deletion issue where sessions appeared to delete but remained in database
  - **DATABASE DELETION**: Fixed delete function to properly remove sessions and all associated chat messages from PostgreSQL
  - **VERIFICATION SYSTEM**: Added deletion verification to ensure sessions are actually removed from database
  - **TRANSACTION SAFETY**: Improved delete function with explicit flush and commit operations plus rollback on failure
  - **LOGGING ENHANCEMENT**: Added detailed logging to track deletion process and verify successful removal
  - **BUG RESOLUTION**: Sessions no longer reappear after deletion - database deletion now works correctly
- July 22, 2025: **FINAL BRANDING UPDATE** - Completed Stay Golden Health client branding across entire application
  - **LOGIN PAGE BRANDING**: Updated login page title and subtitle to use "Stay Golden Health" instead of "Sweats Collective"
  - **TERMINOLOGY CONSISTENCY**: Changed "email AI agent dashboard" to "messenger AI agent dashboard" throughout login interface
  - **COMPLETE REBRAND**: All client-facing text now properly reflects Stay Golden Health branding
- July 22, 2025: **EMAIL NOTIFICATION ENHANCEMENT** - Added Stay Golden Health branding and terminology updates
  - **CLIENT BRANDING**: Added "Stay Golden Health" client name to email subject lines and headers
  - **DASHBOARD URL**: Added proper dashboard link (https://stay-golden-health-messenger-sessions.replit.app/) to email notifications
  - **DATE FORMAT**: Changed email date format to DD/MM/YYYY HH:mm for better readability
  - **TERMINOLOGY UPDATE**: Changed "Customer" to "User Name" across entire application interface
  - **UI CONSISTENCY**: Updated table headers, session details, and all frontend references to use "User Name"
  - **EMAIL TEMPLATE**: Enhanced email template with client branding and proper dashboard access links
- July 22, 2025: **EMAIL NOTIFICATION SYSTEM FIXED** - Resolved field name mismatch preventing QA issue email alerts
  - **BUG FIX**: Fixed `contact_id` vs `customer_id` field name mismatch in email notification template
  - **EMAIL INTEGRATION**: Confirmed Resend API integration working with test email sent successfully (ID: cba3a780-31f1-43ef-95ac-aa9768789acc)
  - **QA WORKFLOW**: Email notifications now properly sent to team@izzyagents.ai when QA status marked as "issue"
  - **ERROR HANDLING**: Email failures are logged but don't break QA update functionality
  - **TESTING**: Manual email test confirmed from noreply@izzyagents.ai to team@izzyagents.ai working
- July 22, 2025: **TIMEZONE ERROR RESOLUTION** - Fixed all timezone comparison issues across dashboard APIs
  - **SESSION DETAILS FIX**: Resolved timezone comparison error in session details retrieval endpoint
  - **CHART COLORS**: Updated Activity Statistics chart colors to perfectly match scorecard colors
  - **API STABILITY**: All stats, daily stats, and session details APIs now working without timezone errors
  - **DATA INTEGRITY**: Session details modal now displays complete conversation data correctly
- July 22, 2025: **DUAL STATUS SYSTEM IMPLEMENTATION** - Added independent completion_status field for better session management
  - **NEW FEATURE**: Added `completion_status` field to MessengerSession model with values: 'complete', 'in_progress', 'incomplete'
  - **SEPARATION OF CONCERNS**: Completion status (ticket progress) now independent from archive status (ticket visibility)
  - **DATABASE SCHEMA**: Added completion_status column with automatic population based on booking URLs and activity timestamps
  - **API ENHANCEMENT**: Updated all endpoints to support both completion_status and status filtering independently
  - **FILTERING SYSTEM**: Users can now filter by completion (all/complete/in_progress/incomplete) AND archive status (all/active/archived) separately
  - **BACKWARDS COMPATIBILITY**: Legacy 'completed' field maintained for existing integrations
  - **DATA INTEGRITY**: 17 total sessions: 1 complete, 1 in_progress, 15 incomplete; 13 active, 4 archived
- July 22, 2025: **SYSTEM ARCHITECTURE UPDATE** - Streamlined database schema for archive functionality
  - **BREAKING CHANGE**: Removed `archived` boolean column from `messenger_sessions` table
  - Updated archive system to use `status='archived'` instead of `archived=true` boolean field
  - Fixed schema validation to accept "archived" as valid status value alongside "active", "resolved", "escalated"
  - Updated all API endpoints and frontend logic to use status-based archiving
  - Archive operations now properly set `status='archived'` when sessions are archived
  - Fixed filter system to correctly show archived sessions when "Archived" status filter is applied
  - Simplified database structure: sessions identified as archived purely by status field
- July 22, 2025: **MAJOR ARCHITECTURAL CHANGE** - Complete Supabase removal and full PostgreSQL consolidation
  - **BREAKING CHANGE**: Completely removed Supabase integration for better CRUD control and simplified architecture
  - Created new `chat_sessions_for_dashboard` table in PostgreSQL with full message storage capabilities
  - Added `ChatSessionForDashboard` model for individual chat messages with proper indexing
  - Migrated all session data and chat messages to PostgreSQL for unified data management
  - Updated all API endpoints to use PostgreSQL exclusively: GET/POST/PUT/DELETE operations
  - Removed `supabase_service.py` and all Supabase dependencies from the codebase
  - Enhanced session creation endpoint to handle both session metadata and individual chat messages
  - All QA functionality, statistics, and session management now operates from single PostgreSQL database
  - Improved performance with proper database joins and aggregations instead of cross-platform queries
  - **Data Migration**: Successfully populated PostgreSQL with test data including completed session with booking URL
  - **Frontend Integration**: Fixed session details modal to work with PostgreSQL API endpoints
  - **Timestamp Management**: Proper `created_at` and `updated_at` timestamps using `datetime.utcnow`
  - **Complete CRUD Operations**: All create, read, update, delete operations now work seamlessly with PostgreSQL
  - **Deletion Safety**: Delete operations properly remove records from both `messenger_sessions` and `chat_sessions_for_dashboard` tables
- July 22, 2025: Fixed critical database architecture issue with status filtering system
  - Removed incorrect `chat_sessions_for_dashboard` table from Replit PostgreSQL (should only exist in Supabase)
  - Corrected data separation: Session data in Supabase, QA/tracking data in PostgreSQL  
  - Fixed status filtering to use PostgreSQL `status` field ("active", "archived") instead of Supabase `completion_status`
  - Updated schema validation to only allow actual PostgreSQL status values
  - Status filter now works correctly with proper database field separation
- July 21, 2025: Enhanced Test AI chat modal with superior z-index and instant completion detection
  - Fixed Test AI modal interaction issues by increasing z-index to 10000 and ensuring pointer events work even when session details modals are open
  - Added instant completion detection that triggers when booking URL (https://shorturl.at/9u9oh) is provided in Test AI chat
  - Test AI chat now auto-updates any open session details modal when new messages are received
  - Completion status updates within 2-5 seconds after booking URL is provided, with visual success notification
  - Test AI modal input areas are always interactive with enhanced CSS pointer-events and z-index controls
- July 21, 2025: Implemented instant archive and delete operations with smooth UI updates
  - Fixed "updateBulkActionControls is not defined" error by adding updateSelectionControls function
  - Archive and delete operations now close modals instantly and remove items immediately with smooth fade-out animation
  - Backend processing happens in background without blocking user interface
  - Both archive and delete functions update statistics instantly for responsive user experience
  - Delete function properly removes sessions from both Replit PostgreSQL AND Supabase databases
  - No more 10+ second delays - UI updates are immediate and smooth
- July 21, 2025: Improved delete functionality and session management
  - Delete sessions now uses Bootstrap modal instead of browser confirm dialog
  - Delete functionality properly removes testing sessions from Supabase database
  - Added smooth row removal animation when sessions are deleted
  - Auto-refresh stats after deletion without full table reload
  - Automatic session addition: new Test AI sessions appear in table with green highlight animation
  - Fixed Test AI chat styling with proper white text and bold sender names on dark backgrounds
- July 21, 2025: Added Test AI functionality with draggable, resizable modal window
  - New "Test AI" button in header next to logout button
  - Draggable and resizable chat interface that floats over the page
  - Real-time conversation testing with simulated AI responses
  - Maintains session state for continuous conversations
  - Can be configured to connect to actual AI webhook endpoints
  - Background page remains fully functional when modal is open
- July 21, 2025: Updated header layout for better user experience
  - Removed username display from header for cleaner design
  - Made logout button horizontal with icon positioned to the left of text
  - Added Test AI button with robot icon for easy AI system testing
- July 21, 2025: Implemented three-state completion system for messenger sessions
  - Complete: Sessions where booking URL (https://shorturl.at/9u9oh) was provided
  - In Progress: Sessions with messages within 12 hours (orange badge)
  - Incomplete: Sessions with no activity for over 12 hours (red badge)
  - Updated scorecard to show 6 smaller cards with all completion and QA statuses
  - Added timezone handling for Sydney time calculations
- July 21, 2025: Email notification system implemented using Resend API for QA issue alerts
  - Replaced n8n webhook with professional email notifications
  - Comprehensive HTML and text email templates with session details, QA notes, and next steps
  - Automated emails sent when QA status is marked as "issue"
  - System gracefully handles email failures without breaking QA functionality
- July 21, 2025: Quality Assurance system fully restored with role-based permissions
  - Successfully restored QA functionality in session details modal with accordions for QA Management and Developer Feedback
  - Created three user accounts with secure passwords and role-based access:
    * IzzyAdmin (password: HUcYi4PHS#h!Htl9) - QA role (can only access QA section)
    * Brooklyn (password: qEmA@B79^4QV6r$i) - QA role (can only access QA section) 
    * IzzyDev (password: dBWmYvLk!XW&wGxG) - Developer role (can access both QA and Developer Feedback sections)
  - QA data stored in Replit PostgreSQL database while session data remains in Supabase
  - API endpoints updated to handle QA operations with PostgreSQL integration
  - Role-based UI controls: QA users see QA section only, developers see both sections
- July 21, 2025: PostgreSQL database successfully configured and streamlined for messenger sessions
  - Created dedicated PostgreSQL database instance with full environment variable setup
  - Removed email_inquiries table as system now focuses exclusively on messenger sessions
  - Refactored API routes to only include messenger session endpoints and authentication
  - Application running successfully with messenger_sessions, users, and errors tables
- July 16, 2025: Added "Reopen Ticket in Gorgias" functionality for archived tickets
  - New API endpoint `/api/inquiries/{id}/reopen-gorgias` to reopen tickets in Gorgias
  - Frontend button appears only for archived tickets with ticket URLs
  - Integrates with Gorgias API to change ticket status from closed to open
  - Updates local ticket status from archived back to engaged
- June 25, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.