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
- **API Endpoints**: Comprehensive RESTful APIs for managing web chat sessions, QA updates, statistics, error logging, and secure conversation retrieval.
- **Quality Assurance System**: Implements a four-state QA workflow (unchecked → passed/issue → fixed) with user attribution and developer feedback.
- **Data Flow**: Sessions are created via web chat widget, processed by AI agent, lead data sent to webhook, displayed on dashboard, and reviewed via QA system.

### System Design Choices
- **Unified Data Storage**: Consolidated all data storage to PostgreSQL.
- **Independent Status Management**: Implemented a dual status system (`completion_status` and `archive_status`) for granular control over session visibility and progress.
- **Real-time Updates**: Designed for immediate UI updates for operations like archiving, deleting, and session additions.
- **Modular Design**: Separation of concerns between backend (Flask, SQLAlchemy) and frontend (Vanilla JS, Bootstrap).
- **Auto-Sync System**: Implemented comprehensive auto-sync mechanisms to prevent orphaned sessions, including smart auto-detection, background processing during API calls, and a manual sync endpoint.
- **Lead Data Separation**: Refactored database architecture to separate lead information into a dedicated `leads` table with foreign key relationships for improved data integrity.

## External Dependencies

### Required Services
- **PostgreSQL**: Main relational database.
- **Facebook Messenger**: Source platform for customer conversational data.
- **Resend Email API**: Used for sending automated QA issue notifications and other email alerts.
- **N8n**: Automation platform for webhook processing.

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
- `BotUI`

## Recent Changes

### August 11, 2025: Production Embed Chat Widget Implementation & Height Fix
**COMPREHENSIVE EMBED CHAT SYSTEM DEPLOYED**: Created fully functional embed chat widget using same webhook infrastructure as dashboard test AI functionality.

**CRITICAL HEIGHT ISSUE RESOLVED**: Fixed 600px height display problems that prevented proper embed chat functionality on external websites.

**KEY FEATURES IMPLEMENTED**:
1. **Production API Endpoint**: Added `/api/embed-chat/send-message` separate from testing functionality
2. **Real-Time AI Communication**: Direct integration with production webhook (https://n8n-g0cw.onrender.com/webhook/44e68b37-d078-44b3-b3bc-2a51a9822aca)
3. **Session Management**: localStorage-based session persistence across browser refreshes
4. **AI-Initiated Conversations**: AI sends first message to start conversation, not user
5. **Modern Chat UI**: Replaced BotUI with custom responsive chat interface
6. **Dashboard Integration**: Sessions created via embed chat automatically appear in dashboard

**UI/UX IMPROVEMENTS**:
- Removed "AI Assistant" branding, changed header to "Get in touch with us to discuss your project"
- Removed "powered by AI chat assistant" footer
- Clean, modern chat interface with proper message bubbles
- Real-time typing indicators during AI responses
- Fixed 600px height rendering issues by removing problematic iframe-resizer dependency
- Implemented reliable fixed-height approach for consistent WordPress embedding

**TECHNICAL ARCHITECTURE**:
- Session continuity: Existing chats resume from localStorage
- Message persistence: Full conversation history stored locally
- Automatic session sync: Session IDs from webhook responses stored for continued conversation
- Error handling: Graceful fallbacks for network issues and webhook unavailability
- iframe optimization: Fixed 600px height for reliable WordPress embedding
- Fallback responses: Chat continues working even when AI webhook is temporarily unavailable

**SESSION FLOW**:
1. User opens embed chat → AI automatically sends greeting message
2. User responds → Message sent to webhook → AI response displayed
3. Session ID stored → Subsequent messages continue same conversation
4. Browser refresh → Previous conversation loaded from localStorage
5. Session appears in dashboard immediately with completion detection

**DEBUGGING UTILITIES**:
- `clearChatSession()`: Reset chat session for testing
- `getChatSession()`: View current session details
- Console logging for webhook requests/responses

**WORDPRESS INTEGRATION UPDATE**:
- Updated embed code in WORDPRESS_INTEGRATION.md to match current design
- Corrected container width (500px → 550px) and implemented fixed 600px height
- Removed problematic iframe-resizer dependency causing height display issues
- Updated documentation to reflect AI-initiated conversations and current data flow
- Fixed webhook payload examples to match production endpoint format
- Added fallback responses for webhook unavailability scenarios

### August 12, 2025: Complete Conversation History API Implementation
**MAJOR API ENHANCEMENT**: Transformed `/api/conversation/<session_id>` endpoint to provide conversation context excluding the most recent AI message.

**COMPREHENSIVE FEATURES IMPLEMENTED**:
1. **Contextual Conversation History**: Returns chronological message thread excluding the last AI response to provide context for AI decision-making
2. **Rich Message Data**: Each message includes ID, content, timestamp, and sender identification
3. **Enhanced Session Metadata**: Provides statistics with `excluded_last_ai_message` flag and accurate counts excluding the most recent AI response
4. **Chronological Ordering**: Messages arranged in conversation flow order for natural reading up to the point before the last AI response
5. **Backward Compatibility**: Maintains existing `last_ai_message` field referring to the excluded message for legacy integrations

**ENHANCED RESPONSE STRUCTURE**:
```json
{
  "session_id": "session_xyz",
  "conversation_history": [
    {
      "id": 123,
      "message": "Hi there!",
      "timestamp": "2025-08-12T05:00:00",
      "sender": "user"
    },
    {
      "id": 124, 
      "message": "Hello! How can I help you?",
      "timestamp": "2025-08-12T05:00:05",
      "sender": "ai"
    },
    {
      "id": 125,
      "message": "I need help with my project",
      "timestamp": "2025-08-12T05:00:10",
      "sender": "user"
    }
  ],
  "session_metadata": {
    "total_messages": 3,
    "ai_messages_count": 1,
    "user_messages_count": 2,
    "session_start": "2025-08-12T05:00:00",
    "session_end": "2025-08-12T05:00:10",
    "excluded_last_ai_message": true
  },
  "last_ai_message": "How can I help with your project?",
  "ai_message_time": "2025-08-12T05:00:15"
}
```

**TECHNICAL IMPLEMENTATION**:
- Retrieves all session messages with optimized database query
- Identifies and excludes the most recent AI message from conversation history
- Orders remaining messages chronologically for natural conversation flow
- Maintains API key authentication and session validation
- Provides accurate metadata reflecting the filtered conversation state
- Preserves backward compatibility with existing integrations

**USE CASE**: External AI systems receive conversation context leading up to the current moment, enabling them to understand the full dialogue context without seeing their own most recent response. This is ideal for AI agents that need to analyze conversation state and provide contextually-aware follow-up responses based on the complete interaction history up to that point.

### August 11, 2025: Fixed Export Session Functionality
**EXPORT SYSTEM REPAIR**: Resolved critical export session bug that prevented IzzyDevs user from exporting chat sessions.

**ISSUE RESOLVED**: Fixed `ai_engaged` field access error - corrected to retrieve from MessengerSession table instead of Lead table where it doesn't exist.

**COMPREHENSIVE EXPORT FEATURES**:
1. **Complete Lead Information**: Export now includes all lead qualification fields even when null
2. **Question Status Visibility**: Shows "Not answered" vs actual responses to identify unanswered qualification questions
3. **Fallback Handling**: Proper handling when no lead record exists with all fields marked as "Not answered"
4. **Dual Export Endpoints**: Fixed both `/api/messenger-sessions/<int:session_id>/export` and `/api/sessions/<session_id>/export` endpoints

**EXPORT CONTENT INCLUDES**:
- Session metadata (ID, timestamps, status, QA information)
- Comprehensive lead qualification data with null field handling
- Complete conversation thread with proper timestamp formatting
- QA notes and developer feedback sections
- Professional formatting for external use

### August 11, 2025: Robust Completion Status Sync System Implementation
**ISSUE RESOLVED**: Dashboard and session details completion status not updating consistently when sessions become complete, even when toast notifications appeared.

**ROOT CAUSE ANALYSIS**: 
- Auto-sync mechanism created messenger sessions with outdated data before completion messages arrived
- Completion detection logic only ran during active chat message processing, missing sessions created via auto-sync
- Database inconsistency between chat_sessions_for_dashboard (with completion messages) and messenger_sessions (with stale status)

**COMPREHENSIVE SOLUTION IMPLEMENTED**:
1. **Enhanced Auto-Sync Completion Detection**: Updated `ensure_messenger_session_exists()` to detect "within 24 hours" messages during session creation and set completion_status to "complete"
2. **Robust Sync Functions**: Enhanced `sync_messenger_session_data()` with completion detection and detailed logging
3. **Completion Status Sync API**: Added `/api/sync-completion-status` endpoint to batch-update all sessions with completion messages
4. **Fixed Runtime Error**: Resolved `has_booking_url` undefined variable error in session details endpoint
5. **Database-First Display**: All endpoints now use stored completion_status from database for consistent display
6. **Real-Time Updates**: Both dashboard stats and session details now update immediately when completion status changes
7. **Comprehensive Logging**: Added detailed logging for all completion status changes and sync operations

**IMMEDIATE FIXES APPLIED**:
- Fixed session_cxunukm7npon98a25965pi and session_s6jswb91ossugqldf5n4l completion status
- Updated message counts and timestamps to reflect actual completion times
- Verified all 3 test sessions now show "Complete" status in both dashboard and session details

**COMPREHENSIVE SOLUTION DEPLOYED**:
- **Multi-Layer Completion Detection**: System now detects completion via 4 mechanisms: live chat handler, auto-sync creation, periodic background checks, and manual sync endpoint
- **Real-Time Updates**: Dashboard and session details update instantly when AI sends "within 24 hours" messages
- **Background Processing**: All major endpoints (sessions list, stats, session details) automatically check and update completion status
- **Database Consistency**: Fixed messenger_sessions and chat_sessions_for_dashboard synchronization issues
- **Automated Logging**: Comprehensive logging tracks all completion status changes for debugging

**VERIFIED WORKING**: 
- Live completion detection: Test session automatically marked complete when AI sent "within 24 hours" message
- Dashboard real-time updates: Stats immediately show correct completion counts
- Session details accuracy: Modal displays proper completion status and message counts
- Background sync: System automatically fixes completion status for existing sessions
- Database integrity: All completion statuses remain consistent across restarts and refreshes

**SYSTEM GUARANTEES**: Every session with "within 24 hours" booking confirmation message will be automatically detected and marked as complete within seconds, with immediate dashboard and UI updates.