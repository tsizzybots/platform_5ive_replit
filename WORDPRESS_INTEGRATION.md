# WordPress Integration Guide for Web Chat AI Lead Generation

## Overview
This guide explains how to embed the AI chat widget into your WordPress website using an iframe. The chat widget collects lead information and sends it to your N8n automation workflows.

## Quick Setup

### 1. Embed the Chat Widget

Add this HTML code to any WordPress page or post where you want the chat widget to appear:

```html
<!-- AI Chat Widget -->
<div id="ai-chat-container" style="width: 100%; max-width: 650px; margin: 20px auto;">
    <iframe 
        id="replit-chat-iframe" 
        src="https://YOUR-REPLIT-DOMAIN.replit.app/embed-chat" 
        style="width: 100%; border: none; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);"
        scrolling="no">
    </iframe>
</div>

<!-- iframe-resizer script for responsive sizing -->
<script src="https://unpkg.com/iframe-resizer/js/iframeResizer.min.js"></script>
<script>
  // Initialize iframe resizer
  iFrameResize({ 
    log: false,
    minHeight: 400,
    autoResize: true,
    checkOrigin: false
  }, '#replit-chat-iframe');
</script>
```

### 2. Replace the Domain

Replace `YOUR-REPLIT-DOMAIN` with your actual Replit app domain, for example:
- `https://web-chat-ai-lead-generation.your-username.replit.app/embed-chat`

### 3. Configure N8n Webhook (Optional)

To receive lead data in N8n, set the environment variable:
```
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id
```

## Advanced Integration

### Customizing the Widget Size

You can adjust the widget container size:

```html
<div id="ai-chat-container" style="width: 100%; max-width: 700px; height: 600px; margin: 20px auto;">
    <!-- iframe here -->
</div>
```

### Adding Custom Styling

Style the container to match your site:

```css
#ai-chat-container {
    margin: 40px auto;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 16px;
}

#replit-chat-iframe {
    box-shadow: 0 12px 48px rgba(0,0,0,0.15);
    border-radius: 16px;
}
```

### Mobile Responsive

For better mobile experience:

```css
@media (max-width: 768px) {
    #ai-chat-container {
        margin: 10px;
        max-width: none;
    }
    
    #replit-chat-iframe {
        height: 70vh;
        min-height: 400px;
    }
}
```

## Widget Features

### Lead Collection Flow
1. **Greeting**: AI welcomes the visitor
2. **Name Collection**: Asks for visitor's name
3. **Email Collection**: Requests email with validation
4. **Interest Selection**: Multiple choice for business needs
5. **Lead Completion**: Sends data to webhook and database

### Data Captured
- Full name
- Email address (validated)
- Interest/inquiry type
- Complete chat transcript
- Session timestamp
- Source tracking (web_chat)

## N8n Webhook Payload

When a lead is completed, the following data is sent to your N8n webhook:

```json
{
  "session_id": "webchat_1642345678901_abc123",
  "name": "John Smith",
  "email": "john@example.com",
  "chat_transcript": [
    {
      "type": "ai",
      "message": "Hello! I'm here to help...",
      "timestamp": "2024-01-16T10:30:00.000Z"
    },
    {
      "type": "user", 
      "message": "John Smith",
      "timestamp": "2024-01-16T10:30:15.000Z"
    }
  ],
  "completed": true,
  "source": "web_chat",
  "timestamp": "2024-01-16T10:35:00.000Z"
}
```

## Dashboard Access

### Admin Dashboard
Access the admin dashboard at:
- `https://YOUR-REPLIT-DOMAIN.replit.app/`

### Dashboard Features
- View all chat sessions (Messenger + Web Chat)
- Filter by session source (Web Chat vs Messenger)
- Quality assurance workflow
- Lead data export
- Webhook delivery status
- Session analytics

## Troubleshooting

### Common Issues

1. **iframe not loading**
   - Check that the Replit domain is correct
   - Ensure the app is running and deployed

2. **Webhook not receiving data**
   - Verify the N8N_WEBHOOK_URL environment variable
   - Check N8n webhook endpoint is active
   - Review webhook logs in the dashboard

3. **Chat not starting**
   - Check browser console for JavaScript errors
   - Ensure all CDN resources are loading

### Testing

Test the integration:
1. Navigate to your WordPress page
2. Interact with the chat widget
3. Complete the lead flow
4. Check the admin dashboard for the new session
5. Verify webhook delivery (if configured)

## Security Considerations

- The iframe uses HTTPS for secure communication
- Email validation prevents basic spam
- Session IDs are unique and timestamped
- Chat data is stored securely in PostgreSQL

## Support

For issues with the chat widget or dashboard:
1. Check the Replit app logs
2. Review the admin dashboard error logs
3. Test the API endpoints directly
4. Verify environment variables are set correctly