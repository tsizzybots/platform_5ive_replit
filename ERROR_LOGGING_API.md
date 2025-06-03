# Error Logging API Documentation

## Overview
This API allows automation systems to log errors and retrieve error information for monitoring and debugging purposes.

## Authentication
- Error creation requires API key authentication via `X-API-Key` header
- Error retrieval requires login session authentication

## Endpoints

### 1. Log New Error
**POST** `/api/errors`

Log a new automation error in the system.

**Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key-here
```

**Request Body:**
```json
{
    "timestamp": "2025-06-03T04:30:00Z",
    "workflow": "email-processing",
    "url": "https://example.com/api/process",
    "node": "process-node-1",
    "error_message": "Failed to process email due to timeout"
}
```

**Field Descriptions:**
- `timestamp` (required): ISO 8601 datetime when the error occurred
- `workflow` (required): Name of the workflow or process where error occurred (max 255 chars)
- `url` (optional): URL where the error occurred (max 500 chars)
- `node` (optional): Specific node or component identifier (max 255 chars)
- `error_message` (required): Detailed error description

**Response (201 Created):**
```json
{
    "status": "success",
    "message": "Error logged successfully",
    "data": {
        "id": 123,
        "timestamp": "2025-06-03T04:30:00Z",
        "workflow": "email-processing",
        "url": "https://example.com/api/process",
        "node": "process-node-1",
        "error_message": "Failed to process email due to timeout",
        "created_at": "2025-06-03T04:30:15Z"
    }
}
```

### 2. List Errors
**GET** `/api/errors`

Retrieve a list of errors with optional filtering and pagination.

**Query Parameters:**
- `workflow` (optional): Filter by workflow name (partial match)
- `date_from` (optional): Filter errors from this date (ISO 8601)
- `date_to` (optional): Filter errors until this date (ISO 8601)
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)

**Example Request:**
```
GET /api/errors?workflow=email&date_from=2025-06-01T00:00:00Z&page=1&per_page=10
```

**Response (200 OK):**
```json
{
    "status": "success",
    "data": {
        "errors": [
            {
                "id": 123,
                "timestamp": "2025-06-03T04:30:00Z",
                "workflow": "email-processing",
                "url": "https://example.com/api/process",
                "node": "process-node-1",
                "error_message": "Failed to process email due to timeout",
                "created_at": "2025-06-03T04:30:15Z"
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 10,
            "total": 45,
            "pages": 5,
            "has_next": true,
            "has_prev": false
        }
    }
}
```

### 3. Get Specific Error
**GET** `/api/errors/{id}`

Retrieve details of a specific error by ID.

**Response (200 OK):**
```json
{
    "status": "success",
    "data": {
        "id": 123,
        "timestamp": "2025-06-03T04:30:00Z",
        "workflow": "email-processing",
        "url": "https://example.com/api/process",
        "node": "process-node-1",
        "error_message": "Failed to process email due to timeout",
        "created_at": "2025-06-03T04:30:15Z"
    }
}
```

### 4. Delete Error
**DELETE** `/api/errors/{id}`

Delete a specific error by ID.

**Response (200 OK):**
```json
{
    "status": "success",
    "message": "Error deleted successfully"
}
```

## Error Responses

All endpoints return consistent error responses:

**Validation Error (400):**
```json
{
    "status": "error",
    "message": "Validation failed",
    "errors": {
        "timestamp": ["Not a valid datetime."],
        "workflow": ["Missing data for required field."]
    }
}
```

**Not Found (404):**
```json
{
    "status": "error",
    "message": "Error not found"
}
```

**Server Error (500):**
```json
{
    "status": "error",
    "message": "Failed to log error",
    "error": "Database connection failed"
}
```

## Usage Examples

### Logging an Error from a Python Script
```python
import requests
from datetime import datetime

def log_error(workflow, error_message, url=None, node=None):
    api_url = "https://your-domain.com/api/errors"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key-here"
    }
    
    data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "workflow": workflow,
        "error_message": error_message,
        "url": url,
        "node": node
    }
    
    response = requests.post(api_url, json=data, headers=headers)
    return response.json()

# Example usage
result = log_error(
    workflow="data-sync",
    error_message="Failed to sync customer data: Connection timeout",
    url="https://api.example.com/customers",
    node="sync-worker-3"
)
```

### Logging an Error from a JavaScript/Node.js Script
```javascript
async function logError(workflow, errorMessage, url = null, node = null) {
    const apiUrl = "https://your-domain.com/api/errors";
    
    const data = {
        timestamp: new Date().toISOString(),
        workflow: workflow,
        error_message: errorMessage,
        url: url,
        node: node
    };
    
    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'your-api-key-here'
        },
        body: JSON.stringify(data)
    });
    
    return await response.json();
}

// Example usage
logError(
    "email-automation",
    "Failed to send notification email: SMTP server unreachable",
    "smtp://mail.example.com:587",
    "email-sender-1"
);
```

## Best Practices

1. **Include Detailed Error Messages**: Provide specific information about what went wrong
2. **Use Consistent Workflow Names**: Use standardized names for easier filtering
3. **Include Context**: Add URL and node information when available
4. **Handle API Failures**: Implement retry logic and fallback error handling
5. **Monitor Regularly**: Set up automated monitoring of error trends