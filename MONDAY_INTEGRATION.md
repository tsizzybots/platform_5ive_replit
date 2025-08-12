# Monday.com Integration Setup Guide

## Overview
The Platform 5ive dashboard now automatically sends completed lead information to Monday.com boards when chat sessions are marked as complete. This integration creates new items in your Monday.com board with all collected lead data.

## Setup Requirements

### 1. Monday.com API Token
You need a Monday.com API token to authenticate requests:

1. Go to your Monday.com profile → **Developers** 
2. Click **API token** → **Show** → **Copy**
3. Or: Profile → **Administration** → **Connections** → **Personal API token**

### 2. Monday.com Board ID
You need the numerical ID of the board where leads should be created:

1. Open your Monday.com board
2. Look at the URL: `https://yourworkspace.monday.com/boards/1234567890`
3. The board ID is the number at the end (e.g., `1234567890`)

### 3. Environment Variables
Set these environment variables in your Replit project:

```bash
MONDAY_API_TOKEN=your_monday_api_token_here
MONDAY_BOARD_ID=1234567890
```

## Lead Data Mapping

The following lead information is automatically sent to Monday.com when a session completes:

### Contact Information
- **Full Name** → Item name (with company if available)
- **Email** → email column
- **Phone Number** → phone column
- **Company Name** → company column

### AI-Related Information
- **AI Interest Reason** → ai_interest column
- **AI Implementation Known** → ai_implementation column
- **AI Budget Allocated** → budget column
- **AI Implementation Timeline** → timeline column

### Business Information
- **Business Challenges** → challenges column
- **Business Goals (6-12m)** → goals column

### Session Metadata
- **Session ID** → session_id column
- **Completion Date** → completion_date column
- **Lead Source** → "Platform 5ive Chat Widget"
- **Status** → "New Lead"

## Column Configuration

**Note:** The column names in the Monday.com service may need to be adjusted based on your specific board setup. To get your board's column structure:

1. Use the board info API endpoint: `GET /api/monday-board-info`
2. Update the `_prepare_column_values` method in `monday_service.py` with your actual column IDs

## Automatic Triggers

Lead information is automatically sent to Monday.com in these scenarios:

1. **Real-time completion**: When an AI message contains "within 24 hours" (booking confirmation)
2. **Background sync**: During periodic completion status updates
3. **Manual sync**: When using the completion sync API endpoint

## Testing the Integration

### Test Connection
```bash
curl -X POST http://localhost:5000/api/test-monday-integration \
  -H "Content-Type: application/json"
```

### Test with Specific Session
```bash
curl -X POST http://localhost:5000/api/test-monday-integration \
  -H "Content-Type: application/json" \
  -d '{"session_id": "session_xyz123"}'
```

### Get Board Structure
```bash
curl -X GET http://localhost:5000/api/monday-board-info
```

## Error Handling

The integration includes comprehensive error handling:

- **Configuration errors**: Logged when API token or board ID missing
- **API failures**: Logged with full error details
- **Network issues**: Graceful timeouts and retry logic
- **Data validation**: Handles missing or invalid lead data

Errors are logged but don't stop the main application flow.

## Monitoring

Monitor Monday.com integration through application logs:

```bash
# Search for Monday.com related logs
grep -i "monday" your_log_file.log

# Look for successful creations
grep "Successfully sent lead to Monday.com" your_log_file.log

# Check for errors
grep "Error sending lead to Monday.com" your_log_file.log
```

## API Endpoints

### Test Integration
- **POST** `/api/test-monday-integration`
- **Payload**: `{"session_id": "optional_session_id"}`
- **Response**: Status of integration test

### Board Information
- **GET** `/api/monday-board-info`
- **Response**: Board structure with column details

### Manual Completion Sync
- **POST** `/api/sync-completion-status`
- **Response**: Updates completion status and triggers Monday.com sync

## Troubleshooting

### Common Issues

1. **"Monday.com not configured"**
   - Check MONDAY_API_TOKEN and MONDAY_BOARD_ID environment variables
   - Ensure API token has proper permissions

2. **"Failed to connect to Monday.com"**
   - Verify API token is valid
   - Check board ID exists and is accessible
   - Confirm network connectivity

3. **"Failed to create Monday.com item"**
   - Check board permissions (must have write access)
   - Verify column mappings match your board structure
   - Review error logs for specific GraphQL errors

### Column Mapping Issues

If lead data isn't appearing correctly:

1. Get your board structure: `GET /api/monday-board-info`
2. Compare with column mappings in `monday_service.py`
3. Update the `_prepare_column_values` method with correct column IDs

### Rate Limits

Monday.com has a rate limit of 5,000 requests per minute. For high-volume usage:

- Monitor API usage
- Implement request batching if needed
- Consider upgrading Monday.com plan for higher limits

## Security Notes

- Store API tokens securely in environment variables
- Never commit API tokens to version control
- Use read/write permissions only for necessary boards
- Monitor API usage for unauthorized access

## Board Setup Recommendations

For optimal integration, create a Monday.com board with these columns:

- Text columns: Full Name, Email, Company, AI Interest, etc.
- Date column: Completion Date
- Status column: Lead Status
- Numbers column: Budget (if needed)
- Timeline column: Implementation Timeline (if needed)

This ensures all lead data is properly captured and displayed in Monday.com.