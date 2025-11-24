// Configuration
const API_BASE_URL = 'http://localhost:8000';

// State
let sessionId = localStorage.getItem('sessionId') || generateSessionId();
let customerId = localStorage.getItem('customerId') || null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    localStorage.setItem('sessionId', sessionId);
    updateCustomerStatus();
    loadChatHistory();
    
    // Event listeners
    document.getElementById('chat-form').addEventListener('submit', handleSubmit);
    document.getElementById('clear-chat-btn').addEventListener('click', clearChat);
});

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function updateCustomerStatus() {
    const statusElement = document.getElementById('customer-status');
    if (customerId) {
        statusElement.textContent = `Customer ID: ${customerId}`;
        statusElement.style.background = 'rgba(76, 175, 80, 0.3)';
    } else {
        statusElement.textContent = 'Customer ID: Not Set';
        statusElement.style.background = 'rgba(255, 255, 255, 0.2)';
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Clear input
    input.value = '';
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Check if setting customer ID
    if (message.toLowerCase().startsWith('set customer')) {
        const parts = message.split(' ');
        if (parts.length >= 3) {
            customerId = parts[2];
            localStorage.setItem('customerId', customerId);
            updateCustomerStatus();
        }
    }
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        // Send message to API
        const response = await fetch(`${API_BASE_URL}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                customer_id: customerId
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response from server');
        }
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Add bot response to chat
        addMessage(data.response, 'bot');
        
    } catch (error) {
        hideTypingIndicator();
        addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        console.error('Error:', error);
    }
}

function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    
    // Remove welcome message if exists
    const welcomeMsg = messagesContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Format the message (convert newlines to <br>)
    contentDiv.innerHTML = formatMessage(text);
    
    // Time removed for cleaner look
    // const timeDiv = document.createElement('div');
    // timeDiv.className = 'message-time';
    // timeDiv.textContent = formatTime(new Date());
    // contentDiv.appendChild(timeDiv);
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMessage(text) {
    // Convert newlines to <br>
    let formatted = text.replace(/\n/g, '<br>');
    
    // Convert **bold** to <strong>
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Convert *italic* to <em>
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // Convert bullet points
    formatted = formatted.replace(/^[•\-]\s/gm, '&bull; ');
    
    // Make links clickable
    formatted = formatted.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank">$1</a>'
    );
    
    // Convert numbered lists to proper HTML (1. 2. 3.)
    formatted = formatted.replace(/^(\d+)\./gm, '<strong>$1.</strong>');
    
    return formatted;
}

function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function showTypingIndicator() {
    document.getElementById('typing-indicator').classList.add('active');
}

function hideTypingIndicator() {
    document.getElementById('typing-indicator').classList.remove('active');
}

async function loadChatHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`);
        
        if (!response.ok) {
            return; // No history or error, that's okay
        }
        
        const data = await response.json();
        
        if (data.history && data.history.length > 0) {
            const messagesContainer = document.getElementById('chat-messages');
            const welcomeMsg = messagesContainer.querySelector('.welcome-message');
            if (welcomeMsg) {
                welcomeMsg.remove();
            }
            
            data.history.forEach(item => {
                addMessageWithTime(item.user_message, 'user', new Date(item.timestamp));
                addMessageWithTime(item.bot_response, 'bot', new Date(item.timestamp));
            });
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

function addMessageWithTime(text, sender, timestamp) {
    const messagesContainer = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMessage(text);
    
    // Time removed for cleaner look
    // const timeDiv = document.createElement('div');
    // timeDiv.className = 'message-time';
    // timeDiv.textContent = formatTime(timestamp);
    // contentDiv.appendChild(timeDiv);
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
}

async function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history?')) {
        return;
    }
    
    try {
        // Delete from server
        await fetch(`${API_BASE_URL}/chat/history/${sessionId}`, {
            method: 'DELETE'
        });
        
        // Generate new session
        sessionId = generateSessionId();
        localStorage.setItem('sessionId', sessionId);
        
        // Clear UI
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <h2>Welcome to Your E-Commerce Assistant! 👋</h2>
                <p>I'm your AI-powered shopping companion, here to make your online shopping experience seamless and enjoyable!</p>
                <p><strong>How I can help you:</strong></p>
                <ul>
                    <li>🔍 <strong>Search for products</strong> - Find exactly what you're looking for</li>
                    <li>📦 <strong>Track your orders</strong> - Check order status and history</li>
                    <li>⭐ <strong>Get recommendations</strong> - Discover top-rated products</li>
                    <li>📊 <strong>Priority orders</strong> - View high-priority order information</li>
                </ul>
                <p class="tip">💡 <strong>Pro Tip:</strong> Set your customer ID using: <code>set customer &lt;id&gt;</code> to access your order history!</p>
                <p class="example-queries">
                    <strong>Try asking me:</strong><br>
                    • "Show me laptops under $1000"<br>
                    • "What are the best wireless headphones?"<br>
                    • "Show my recent orders"
                </p>
            </div>
        `;
        
    } catch (error) {
        console.error('Error clearing chat:', error);
        alert('Failed to clear chat history');
    }
}
