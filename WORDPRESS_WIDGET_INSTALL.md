# WordPress Chat Widget Installation Guide

## Quick Installation

### Step 1: Copy the Widget Code

Copy this complete code snippet:

```html
<!-- AI Chat Widget -->
<div id="ai-chat-container" style="width: 100%; max-width: 550px; margin: 20px auto;">
    <iframe 
        id="replit-chat-iframe" 
        src="https://platform-5ive-lead-ai.replit.app/embed-chat" 
        style="width: 100%; height: 600px; border: none; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);"
        scrolling="no">
    </iframe>
</div>

<!-- Auto-resize handler -->
<script>
  window.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'resize') {
      const iframe = document.getElementById('replit-chat-iframe');
      if (iframe) {
        iframe.style.height = event.data.height + 'px';
      }
    }
  });
</script>
```

### Step 2: Add to WordPress Page

#### Method 1: Using WordPress Block Editor (Gutenberg)

1. **Edit your page/post** - Go to the WordPress page where you want the chat widget
2. **Add HTML Block** - Click the "+" button to add a new block
3. **Search for "Custom HTML"** - Type "Custom HTML" in the block search
4. **Select Custom HTML block** - Click on it to add it to your page
5. **Paste the code** - Copy and paste the entire widget code from Step 1
6. **Preview** - Click "Preview" to see how it looks
7. **Publish/Update** - Click "Update" or "Publish" to save changes

#### Method 2: Using Classic Editor

1. **Edit your page/post** - Go to the WordPress page where you want the chat widget
2. **Switch to Text tab** - Click the "Text" tab (not "Visual")
3. **Paste the code** - Copy and paste the entire widget code from Step 1
4. **Preview** - Click "Preview" to see how it looks
5. **Update** - Click "Update" to save changes

#### Method 3: Using WordPress Widget Area

1. **Go to Appearance > Widgets** - In your WordPress admin
2. **Add HTML widget** - Drag a "Custom HTML" widget to your desired widget area
3. **Paste the code** - Copy and paste the entire widget code from Step 1
4. **Save** - Click "Save" to apply changes

## Customization Options

### Adjust Widget Size

Change the container size by modifying these values:

```html
<div id="ai-chat-container" style="width: 100%; max-width: 550px; height: 600px; margin: 20px auto;">
```

- `max-width: 550px` - Maximum width of the widget
- `height: 600px` - Fixed height (auto-resize will override this)
- `margin: 20px auto` - Spacing around the widget

### Custom Styling

Add this CSS to your WordPress theme (Appearance > Customize > Additional CSS):

```css
/* Basic styling */
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

/* Mobile responsive */
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

/* Hide on small screens if needed */
@media (max-width: 480px) {
    #ai-chat-container {
        display: none;
    }
}
```

### Positioning Options

#### Center on Page
```html
<div id="ai-chat-container" style="width: 100%; max-width: 550px; margin: 20px auto; text-align: center;">
```

#### Float Right
```html
<div id="ai-chat-container" style="width: 400px; float: right; margin: 20px 0 20px 20px;">
```

#### Full Width
```html
<div id="ai-chat-container" style="width: 100%; margin: 20px 0;">
```

## Advanced Installation

### Adding to Theme Template

If you want the widget to appear on multiple pages, add it to your theme:

1. **Go to Appearance > Theme Editor**
2. **Select the template file** (e.g., `page.php`, `single.php`)
3. **Add the code** where you want the widget to appear
4. **Update file**

### Using Shortcode (requires additional setup)

Create a custom shortcode by adding this to your theme's `functions.php`:

```php
function ai_chat_widget_shortcode() {
    return '<div id="ai-chat-container" style="width: 100%; max-width: 550px; margin: 20px auto;">
        <iframe 
            id="replit-chat-iframe" 
            src="https://platform-5ive-lead-ai.replit.app/embed-chat" 
            style="width: 100%; height: 600px; border: none; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);"
            scrolling="no">
        </iframe>
    </div>
    <script>
      window.addEventListener("message", function(event) {
        if (event.data && event.data.type === "resize") {
          const iframe = document.getElementById("replit-chat-iframe");
          if (iframe) {
            iframe.style.height = event.data.height + "px";
          }
        }
      });
    </script>';
}
add_shortcode('ai_chat_widget', 'ai_chat_widget_shortcode');
```

Then use `[ai_chat_widget]` anywhere in your content.

## Testing

1. **View your page** - Visit the page where you added the widget
2. **Test the chat** - Click on the chat widget to ensure it loads
3. **Complete a conversation** - Test the full lead collection flow
4. **Check mobile** - Test on mobile devices for responsiveness

## Common Issues

### Widget Not Showing
- Check that you pasted the code correctly
- Ensure you're viewing the published page (not draft)
- Clear any caching plugins

### iframe Not Loading
- Check your browser's console for errors
- Ensure the Replit app URL is correct and accessible
- Some security plugins may block iframes

### Mobile Display Issues
- Add the mobile CSS provided above
- Test different screen sizes
- Adjust the responsive breakpoints as needed

## What the Widget Does

- **AI starts conversation** - Automatically greets visitors
- **Collects lead information** - Name, email, company details
- **Stores chat data** - All conversations are saved
- **Sends to automation** - Lead data flows to your systems
- **Mobile responsive** - Works on all devices

That's it! Your WordPress site now has an AI-powered lead generation chat widget.