// Configuration
const API_BASE_URL = 'http://localhost:8000';

// State
let sessionId = localStorage.getItem('sessionId') || generateSessionId();

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    localStorage.setItem('sessionId', sessionId);
    loadChatHistory();
    
    // Event listeners
    document.getElementById('chat-form').addEventListener('submit', handleSubmit);
    
    const clearBtn = document.getElementById('clear-chat-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearChat);
        console.log('Clear button listener attached');
    } else {
        console.error('Clear button not found!');
    }
    
    // Add click handlers to example queries
    attachExampleQueryHandlers();
});

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
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
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response from server');
        }
        
        const data = await response.json();
        
        // Log debug info to console
        if (data.debug_info) {
            console.group('🔍 Query Debug Info');
            console.log('Query:', message);
            console.log('Query Type:', data.debug_info.query_type);
            if (data.debug_info.sql_query) {
                console.log('Generated SQL:', data.debug_info.sql_query);
            }
            if (data.debug_info.sql_results) {
                console.log('SQL Results:', data.debug_info.sql_results);
            }
            if (data.debug_info.error) {
                console.error('Error:', data.debug_info.error);
            }
            console.groupEnd();
        }
        
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

function attachExampleQueryHandlers() {
    // Attach click handlers to example query items
    const exampleQueries = document.querySelectorAll('.example-queries li');
    exampleQueries.forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            const query = item.textContent.replace(/^["']|["']$/g, ''); // Remove quotes
            const input = document.getElementById('message-input');
            input.value = query;
            input.focus();
            // Optionally auto-submit
            // document.getElementById('chat-form').dispatchEvent(new Event('submit'));
        });
    });
}

async function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history?')) {
        return;
    }
    
    try {
        // Delete from server
        const response = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            console.warn('Failed to delete from server, continuing with local clear');
        }
        
        // Generate new session
        sessionId = generateSessionId();
        localStorage.setItem('sessionId', sessionId);
        
        // Clear UI
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <h2>👋 Welcome, Admin</h2>
                <p>I have full access to your database. Ask me anything about your e-commerce data!</p>
                <div class="example-queries">
                    <p><strong>Try asking:</strong></p>
                    <ul>
                        <li>"Show me the top 5 selling products"</li>
                        <li>"How many pending orders do we have?"</li>
                        <li>"List recent customer reviews"</li>
                        <li>"What's our total revenue this month?"</li>
                    </ul>
                </div>
            </div>
        `;
        
        // Re-attach handlers after clearing
        attachExampleQueryHandlers();
        
    } catch (error) {
        console.error('Error clearing chat:', error);
        alert('Failed to clear chat history');
    }
}
