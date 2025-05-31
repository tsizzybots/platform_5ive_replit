# Gorgias AI Agent Integration Guide

## API Base URL
Your Flask application base URL (e.g., `https://your-app-domain.replit.app`)

## Authentication
All API requests require an API key in the header:
```
X-API-Key: your-api-key-here
```

**Setting up API Key:**
Set the `API_KEY` environment variable in your Replit project or deployment.

---

## Primary Integration Endpoints

### 1. Create New Ticket (From Gorgias)

**Endpoint:** `POST /api/inquiries`

**Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key-here
```

**Request Body:**
```json
{
  "ticket_id": "GORGIAS-123456",
  "subject": "Return request for order #54321",
  "body": "Hi, I would like to return my recent order as the size doesn't fit properly. The item was delivered yesterday and is in perfect condition. Can you please help me with the return process?",
  "sender_email": "customer@example.com",
  "sender_name": "John Smith",
  "received_date": "2025-05-31T10:30:00Z"
}
```

**Field Descriptions:**
- `ticket_id` (required): Unique Gorgias ticket ID
- `subject` (required): Email subject line
- `body` (required): Full email content
- `sender_email` (required): Customer's email address
- `sender_name` (optional): Customer's name
- `received_date` (required): When the email was received (ISO 8601 format)

**Success Response (201):**
```json
{
  "status": "success",
  "message": "Email inquiry created successfully",
  "data": {
    "id": 1,
    "ticket_id": "GORGIAS-123456",
    "subject": "Return request for order #54321",
    "body": "Hi, I would like to return my recent order...",
    "sender_email": "customer@example.com",
    "sender_name": "John Smith",
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

### 2. Update Ticket (AI Decision)

**Endpoint:** `PUT /api/inquiries/{id}`

**Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key-here
```

**Use Cases:**

#### AI Decides to Engage (Send Response):
```json
{
  "status": "processed",
  "engaged": true,
  "ai_response": "Thank you for contacting us about your return request. I have processed your return for order #54321. A return shipping label has been sent to your email address. Please package the item securely and attach the label. Once we receive the item, your refund will be processed within 3-5 business days."
}
```

#### AI Decides NOT to Engage (Ignore):
```json
{
  "status": "ignored",
  "engaged": false
}
```

#### Mark as Pending (Need Review):
```json
{
  "status": "pending",
  "engaged": false
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Email inquiry updated successfully",
  "data": {
    "id": 1,
    "ticket_id": "GORGIAS-123456",
    "status": "processed",
    "engaged": true,
    "ai_response": "Thank you for contacting us...",
    "updated_at": "2025-05-31T10:35:00"
  }
}
```

---

## Error Responses

### 401 - Invalid API Key
```json
{
  "status": "error",
  "message": "Invalid or missing API key"
}
```

### 400 - Validation Error
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

### 404 - Ticket Not Found
```json
{
  "status": "error",
  "message": "Email inquiry not found"
}
```

---

## Python Integration Examples

### Example 1: Send New Ticket from Gorgias
```python
import requests
import json
from datetime import datetime

def send_ticket_to_ai_system(gorgias_ticket):
    """Send a new Gorgias ticket to the AI system for processing"""
    
    url = "https://your-app-domain.replit.app/api/inquiries"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key-here"
    }
    
    payload = {
        "ticket_id": f"GORGIAS-{gorgias_ticket['id']}",
        "subject": gorgias_ticket['subject'],
        "body": gorgias_ticket['messages'][0]['body_text'],
        "sender_email": gorgias_ticket['customer']['email'],
        "sender_name": gorgias_ticket['customer']['name'],
        "received_date": gorgias_ticket['created_datetime']
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        result = response.json()
        print(f"Ticket {payload['ticket_id']} logged successfully")
        return result['data']['id']  # Return database ID for updates
    else:
        print(f"Failed to log ticket: {response.json()}")
        return None
```

### Example 2: Update Ticket with AI Decision
```python
def update_ticket_with_ai_decision(db_id, should_engage, ai_response=None):
    """Update ticket based on AI agent's decision"""
    
    url = f"https://your-app-domain.replit.app/api/inquiries/{db_id}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key-here"
    }
    
    if should_engage:
        payload = {
            "status": "processed",
            "engaged": True,
            "ai_response": ai_response
        }
    else:
        payload = {
            "status": "ignored", 
            "engaged": False
        }
    
    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print(f"Ticket {db_id} updated successfully")
        return True
    else:
        print(f"Failed to update ticket: {response.json()}")
        return False
```

### Example 3: Complete Gorgias Integration Workflow
```python
import requests
from datetime import datetime

class GorgiasAIIntegration:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
    
    def process_gorgias_ticket(self, gorgias_ticket):
        """Complete workflow: log ticket and process with AI"""
        
        # Step 1: Log the ticket
        db_id = self.log_ticket(gorgias_ticket)
        if not db_id:
            return False
        
        # Step 2: AI analyzes the ticket
        should_engage, ai_response = self.analyze_ticket_with_ai(gorgias_ticket)
        
        # Step 3: Update based on AI decision
        return self.update_ticket_decision(db_id, should_engage, ai_response)
    
    def log_ticket(self, gorgias_ticket):
        """Log new ticket from Gorgias"""
        payload = {
            "ticket_id": f"GORGIAS-{gorgias_ticket['id']}",
            "subject": gorgias_ticket['subject'],
            "body": gorgias_ticket['messages'][0]['body_text'],
            "sender_email": gorgias_ticket['customer']['email'],
            "sender_name": gorgias_ticket['customer']['name'],
            "received_date": gorgias_ticket['created_datetime']
        }
        
        response = requests.post(
            f"{self.api_url}/api/inquiries",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 201:
            return response.json()['data']['id']
        return None
    
    def analyze_ticket_with_ai(self, ticket):
        """Your AI logic to decide whether to engage"""
        # Example AI logic (replace with your actual AI analysis)
        subject = ticket['subject'].lower()
        body = ticket['messages'][0]['body_text'].lower()
        
        # Engage with return/exchange requests
        if any(keyword in subject or keyword in body for keyword in 
               ['return', 'exchange', 'refund', 'size', 'damaged', 'wrong item']):
            ai_response = self.generate_return_response(ticket)
            return True, ai_response
        
        # Ignore spam or promotional content
        if any(keyword in subject or keyword in body for keyword in 
               ['win', 'prize', 'congratulations', 'million', 'lottery']):
            return False, None
        
        # Default: mark as pending for human review
        return False, None
    
    def generate_return_response(self, ticket):
        """Generate AI response for return requests"""
        return f"""Thank you for contacting us about your inquiry. I have processed your request and a customer service representative will follow up with you within 24 hours. If this is regarding a return or exchange, please have your order number ready for faster assistance.

Best regards,
Customer Service Team"""
    
    def update_ticket_decision(self, db_id, should_engage, ai_response):
        """Update ticket with AI decision"""
        payload = {
            "status": "processed" if should_engage else "ignored",
            "engaged": should_engage
        }
        
        if should_engage and ai_response:
            payload["ai_response"] = ai_response
        
        response = requests.put(
            f"{self.api_url}/api/inquiries/{db_id}",
            headers=self.headers,
            json=payload
        )
        
        return response.status_code == 200

# Usage example:
ai_integration = GorgiasAIIntegration(
    api_url="https://your-app-domain.replit.app",
    api_key="your-api-key-here"
)

# Process a Gorgias webhook
def handle_gorgias_webhook(gorgias_ticket_data):
    success = ai_integration.process_gorgias_ticket(gorgias_ticket_data)
    if success:
        print("Ticket processed and logged successfully")
    else:
        print("Failed to process ticket")
```

---

## cURL Examples for Testing

### Create Ticket:
```bash
curl -X POST https://your-app-domain.replit.app/api/inquiries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "ticket_id": "GORGIAS-123456",
    "subject": "Return request for order #54321",
    "body": "Hi, I would like to return my recent order as the size doesnt fit properly.",
    "sender_email": "customer@example.com",
    "sender_name": "John Smith",
    "received_date": "2025-05-31T10:30:00Z"
  }'
```

### Update Ticket (Engaged):
```bash
curl -X PUT https://your-app-domain.replit.app/api/inquiries/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "status": "processed",
    "engaged": true,
    "ai_response": "Thank you for your return request. A return label has been sent to your email."
  }'
```

### Update Ticket (Ignored):
```bash
curl -X PUT https://your-app-domain.replit.app/api/inquiries/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "status": "ignored",
    "engaged": false
  }'
```

---

## Dashboard Access

The web dashboard is available at your application's root URL and provides:
- Real-time metrics on engagement rates
- Filtered views of engaged vs non-engaged tickets
- Detailed ticket information and AI responses
- Light/dark mode toggle

No API key required for dashboard access - it's for internal monitoring only.