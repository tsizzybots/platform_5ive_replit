# Email Helpdesk API Endpoints

## Base URL
All API endpoints are relative to your application's base URL.

## Authentication
Currently, no authentication is required for these endpoints.

---

## 1. Create New Ticket

**POST** `/api/inquiries`

Creates a new email inquiry ticket in the system.

### Request Body
```json
{
  "ticket_id": "TICKET-12345",
  "subject": "Return request for order #12345",
  "body": "I would like to return my recent order as it doesn't fit properly.",
  "sender_email": "customer@example.com",
  "sender_name": "John Doe",
  "received_date": "2025-05-31T10:30:00Z"
}
```

### Required Fields
- `ticket_id`: Unique identifier for the ticket (string, max 100 chars)
- `subject`: Email subject line (string, max 1000 chars)
- `body`: Email content (string)
- `sender_email`: Valid email address
- `received_date`: ISO 8601 datetime string

### Optional Fields
- `sender_name`: Customer's name (string, max 255 chars)

### Response
```json
{
  "status": "success",
  "message": "Email inquiry created successfully",
  "data": {
    "id": 1,
    "ticket_id": "TICKET-12345",
    "subject": "Return request for order #12345",
    "body": "I would like to return my recent order as it doesn't fit properly.",
    "sender_email": "customer@example.com",
    "sender_name": "John Doe",
    "received_date": "2025-05-31T10:30:00",
    "status": "pending",
    "engaged": false,
    "ai_response": null,
    "created_at": "2025-05-31T10:31:00",
    "updated_at": "2025-05-31T10:31:00"
  }
}
```

---

## 2. Update Ticket Status

**PUT** `/api/inquiries/{inquiry_id}`

Updates the status, engagement, and AI response for an existing ticket.

### URL Parameters
- `inquiry_id`: Database ID of the inquiry (integer)

### Request Body
```json
{
  "status": "processed",
  "engaged": true,
  "ai_response": "Thank you for contacting us. We've processed your return request and sent you a return label via email."
}
```

### Available Fields
- `status`: "pending", "processed", or "ignored"
- `engaged`: true or false
- `ai_response`: Text response from AI agent (optional)

### Response
```json
{
  "status": "success",
  "message": "Email inquiry updated successfully",
  "data": {
    "id": 1,
    "ticket_id": "TICKET-12345",
    "subject": "Return request for order #12345",
    "body": "I would like to return my recent order as it doesn't fit properly.",
    "sender_email": "customer@example.com",
    "sender_name": "John Doe",
    "received_date": "2025-05-31T10:30:00",
    "status": "processed",
    "engaged": true,
    "ai_response": "Thank you for contacting us. We've processed your return request and sent you a return label via email.",
    "created_at": "2025-05-31T10:31:00",
    "updated_at": "2025-05-31T10:35:00"
  }
}
```

---

## 3. Get Single Ticket

**GET** `/api/inquiries/{inquiry_id}`

Retrieves details for a specific ticket.

### URL Parameters
- `inquiry_id`: Database ID of the inquiry (integer)

### Response
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "ticket_id": "TICKET-12345",
    "subject": "Return request for order #12345",
    "body": "I would like to return my recent order as it doesn't fit properly.",
    "sender_email": "customer@example.com",
    "sender_name": "John Doe",
    "received_date": "2025-05-31T10:30:00",
    "status": "processed",
    "engaged": true,
    "ai_response": "Thank you for contacting us. We've processed your return request and sent you a return label via email.",
    "created_at": "2025-05-31T10:31:00",
    "updated_at": "2025-05-31T10:35:00"
  }
}
```

---

## 4. List Tickets with Filters

**GET** `/api/inquiries`

Retrieves a paginated list of tickets with optional filtering.

### Query Parameters
- `status`: Filter by status ("pending", "processed", "ignored")
- `engaged`: Filter by engagement (true/false)
- `ticket_id`: Filter by specific ticket ID
- `sender_email`: Filter by sender email
- `date_from`: Filter tickets received after this date (ISO 8601)
- `date_to`: Filter tickets received before this date (ISO 8601)
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

### Example Requests

Get all engaged tickets:
```
GET /api/inquiries?engaged=true
```

Get pending tickets from a specific email:
```
GET /api/inquiries?status=pending&sender_email=customer@example.com
```

Get tickets by ticket ID:
```
GET /api/inquiries?ticket_id=TICKET-12345
```

### Response
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "ticket_id": "TICKET-12345",
      "subject": "Return request for order #12345",
      "body": "I would like to return my recent order as it doesn't fit properly.",
      "sender_email": "customer@example.com",
      "sender_name": "John Doe",
      "received_date": "2025-05-31T10:30:00",
      "status": "processed",
      "engaged": true,
      "ai_response": "Thank you for contacting us. We've processed your return request and sent you a return label via email.",
      "created_at": "2025-05-31T10:31:00",
      "updated_at": "2025-05-31T10:35:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

## 5. Get Statistics

**GET** `/api/inquiries/stats`

Retrieves summary statistics about all tickets.

### Response
```json
{
  "status": "success",
  "data": {
    "total_inquiries": 150,
    "engaged_inquiries": 45,
    "pending_inquiries": 20,
    "processed_inquiries": 100,
    "ignored_inquiries": 30,
    "engagement_rate": 30.0
  }
}
```

---

## 6. Delete Ticket

**DELETE** `/api/inquiries/{inquiry_id}`

Deletes a specific ticket from the system.

### URL Parameters
- `inquiry_id`: Database ID of the inquiry (integer)

### Response
```json
{
  "status": "success",
  "message": "Email inquiry deleted successfully"
}
```

---

## Error Responses

All endpoints return error responses in this format:

### Validation Error (400)
```json
{
  "status": "error",
  "message": "Validation failed",
  "errors": {
    "sender_email": ["Not a valid email address."],
    "ticket_id": ["Missing data for required field."]
  }
}
```

### Not Found (404)
```json
{
  "status": "error",
  "message": "Email inquiry not found"
}
```

### Server Error (500)
```json
{
  "status": "error",
  "message": "Failed to create email inquiry",
  "error": "Database connection failed"
}
```

---

## Usage Examples for AI Agent Integration

### 1. Incoming Email Processing
When your AI agent receives a new email:

```python
import requests
import json
from datetime import datetime

def process_incoming_email(email_data):
    # Create ticket in database
    ticket_data = {
        "ticket_id": f"TICKET-{email_data['message_id']}",
        "subject": email_data['subject'],
        "body": email_data['body'],
        "sender_email": email_data['from_email'],
        "sender_name": email_data.get('from_name'),
        "received_date": datetime.now().isoformat()
    }
    
    response = requests.post(
        "http://your-app-url/api/inquiries",
        json=ticket_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 201:
        ticket = response.json()['data']
        return ticket['id']  # Return database ID for further processing
    else:
        print(f"Failed to create ticket: {response.json()}")
        return None
```

### 2. AI Decision Making
After analyzing the email content:

```python
def update_ticket_decision(inquiry_id, should_engage, ai_response=None):
    update_data = {
        "engaged": should_engage,
        "status": "processed" if should_engage else "ignored"
    }
    
    if should_engage and ai_response:
        update_data["ai_response"] = ai_response
    
    response = requests.put(
        f"http://your-app-url/api/inquiries/{inquiry_id}",
        json=update_data,
        headers={"Content-Type": "application/json"}
    )
    
    return response.status_code == 200
```

### 3. Monitoring and Analytics
Get statistics for monitoring:

```python
def get_daily_stats():
    response = requests.get("http://your-app-url/api/inquiries/stats")
    if response.status_code == 200:
        stats = response.json()['data']
        print(f"Engagement Rate: {stats['engagement_rate']}%")
        print(f"Pending Tickets: {stats['pending_inquiries']}")
        return stats
    return None
```

### 4. Filter Engaged Tickets
Get all tickets that were engaged with:

```python
def get_engaged_tickets():
    response = requests.get(
        "http://your-app-url/api/inquiries?engaged=true&per_page=100"
    )
    if response.status_code == 200:
        return response.json()['data']
    return []
```