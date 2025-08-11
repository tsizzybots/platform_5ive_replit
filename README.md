# Platform 5ive - AI Lead Generation Dashboard

A sophisticated Flask-powered AI-driven lead generation and customer support dashboard that provides intelligent communication tracking and dynamic engagement tools.

## Features

### 🤖 AI-Powered Lead Generation
- **Embeddable Chat Widget**: BotUI-powered chat interface for WordPress integration
- **Real-time Completion Detection**: Automatically detects when AI provides booking confirmations
- **Lead Data Collection**: Captures visitor information and complete chat transcripts
- **Webhook Integration**: Sends completed leads to N8n automation workflows

### 📊 Comprehensive Dashboard
- **Session Management**: Track and monitor all chat conversations
- **Completion Status Tracking**: Real-time updates when sessions are completed
- **Quality Assurance System**: Four-state QA workflow (unchecked → passed/issue → fixed)
- **User Role Management**: Admin and agent roles with appropriate permissions
- **Advanced Filtering**: Filter sessions by date, completion status, and QA status

### 🔧 Technical Capabilities
- **Multi-Layer Completion Detection**: 4 mechanisms ensure no completed sessions are missed
- **Auto-Sync System**: Prevents orphaned sessions and maintains data consistency
- **Background Processing**: Automatic status updates across all endpoints
- **Real-time Updates**: Dashboard and session details update instantly
- **Database Integrity**: Comprehensive sync between chat data and session metadata

## Technology Stack

### Backend
- **Flask 3.1+**: Web framework with SQLAlchemy ORM
- **PostgreSQL 16**: Robust relational database
- **Gunicorn**: Production WSGI server
- **Marshmallow**: Data serialization and validation
- **JWT & Session Auth**: Secure authentication system

### Frontend
- **Vanilla JavaScript**: Framework-agnostic frontend
- **Bootstrap 5.3**: Responsive UI framework
- **Chart.js**: Data visualization
- **Font Awesome 6.0**: Consistent iconography
- **BotUI**: Chat interface for lead generation

### External Integrations
- **Resend Email API**: Automated QA notifications
- **N8n**: Automation platform for webhook processing
- **Facebook Messenger**: Source platform integration

## System Architecture

### Data Flow
1. **Session Creation**: Via web chat widget or auto-sync from external sources
2. **AI Processing**: Real-time conversation handling with completion detection
3. **Lead Qualification**: Automatic data extraction and storage
4. **Webhook Delivery**: Completed leads sent to automation workflows
5. **QA Review**: Team oversight with feedback system

### Completion Detection System
- **Live Chat Handler**: Detects "within 24 hours" messages during active conversations
- **Auto-Sync Creation**: Checks for completion during session synchronization
- **Background Processing**: Periodic status updates across all major endpoints
- **Manual Sync**: Batch update endpoint for troubleshooting

## Recent Improvements (August 2025)

### Robust Completion Status Automation ✅
- **Multi-Layer Detection**: Comprehensive completion detection via 4 different mechanisms
- **Real-Time Updates**: Dashboard and session details update instantly when AI sends booking confirmations
- **Background Sync**: Automatic completion status fixes for existing sessions
- **Database Consistency**: Resolved synchronization issues between chat data and session metadata
- **System Guarantees**: Every session with "within 24 hours" booking message automatically detected within seconds

### Key Benefits
- **Zero Manual Intervention**: Completion status updates automatically for all scenarios
- **Immediate UI Feedback**: Dashboard stats reflect current state without refresh
- **Data Integrity**: Consistent completion status across restarts and refreshes
- **Comprehensive Logging**: Detailed tracking of all completion status changes

## Security Features
- Session-based authentication with secure password hashing
- Role-based access control (admin/agent permissions)
- API key protection for webhook endpoints
- Environment variable management for sensitive data

## Development Guidelines
- Uses simple, everyday language for non-technical users
- Prioritizes data integrity with real authentication sources
- Implements comprehensive error handling and logging
- Maintains separation of concerns between backend and frontend

## Deployment
- Optimized for Replit auto-scaling deployment
- Gunicorn WSGI server for production performance
- PostgreSQL database with connection pooling
- Environment-based configuration management

---

*Built with ❤️ for efficient AI-powered lead generation and customer support*