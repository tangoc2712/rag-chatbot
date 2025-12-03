// Configuration
const API_BASE_URL = 'http://localhost:8000';

// State - use role-specific session storage
let sessionId = localStorage.getItem(`sessionId_${CHAT_CONFIG.role}`) || generateSessionId();
let customerId = CHAT_CONFIG.customerId;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    localStorage.setItem(`sessionId_${CHAT_CONFIG.role}`, sessionId);
    loadChatHistory();
    
    // Event listeners
    document.getElementById('chat-form').addEventListener('submit', handleSubmit);
    
    const clearBtn = document.getElementById('clear-chat-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearChat);
    }
    
    // Handle user ID input for user/admin modes
    const userIdInput = document.getElementById('user-id-input');
    if (userIdInput) {
        userIdInput.addEventListener('change', (e) => {
            customerId = e.target.value.trim() || null;
            CHAT_CONFIG.customerId = customerId;
            console.log('Updated customer ID:', customerId);
        });
    }
    
    const adminIdInput = document.getElementById('admin-id-input');
    if (adminIdInput) {
        adminIdInput.addEventListener('change', (e) => {
            customerId = e.target.value.trim() || null;
            CHAT_CONFIG.customerId = customerId;
            console.log('Updated admin ID:', customerId);
        });
    }
    
    // Add click handlers to example queries
    attachExampleQueryHandlers();
});

function generateSessionId() {
    return `session_${CHAT_CONFIG.role}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
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
        // Build request body based on role
        const requestBody = {
            message: message,
            session_id: sessionId
        };
        
        // Add customer_id for user and admin modes
        if (CHAT_CONFIG.role !== 'visitor' && CHAT_CONFIG.customerId) {
            requestBody.customer_id = CHAT_CONFIG.customerId;
        }
        
        console.log('Sending request:', requestBody);
        
        // Send message to API
        const response = await fetch(`${API_BASE_URL}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response from server');
        }
        
        const data = await response.json();
        
        // Log debug info to console
        if (data.debug_info) {
            console.group(`🔍 ${CHAT_CONFIG.role.toUpperCase()} Query Debug Info`);
            console.log('Query:', message);
            console.log('Role:', data.debug_info.user_role);
            console.log('Query Type:', data.debug_info.query_type);
            console.log('Data Accessed:', data.debug_info.data_accessed);
            if (data.debug_info.search_results_count) {
                console.log('Results Count:', data.debug_info.search_results_count);
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
    
    // Format the message
    contentDiv.innerHTML = formatMessage(text);
    
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
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
}

function attachExampleQueryHandlers() {
    const exampleQueries = document.querySelectorAll('.example-queries li');
    exampleQueries.forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            const query = item.textContent.replace(/^["']|["']$/g, ''); // Remove quotes
            const input = document.getElementById('message-input');
            input.value = query;
            input.focus();
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
        localStorage.setItem(`sessionId_${CHAT_CONFIG.role}`, sessionId);
        
        // Build example queries HTML
        const examplesHtml = CHAT_CONFIG.exampleQueries
            .map(q => `<li>${q}</li>`)
            .join('');
        
        // Get role-specific styling
        let accessInfoStyle = '';
        let accessInfoContent = '';
        
        if (CHAT_CONFIG.role === 'visitor') {
            accessInfoStyle = 'background: rgba(102, 126, 234, 0.2); border-left: 4px solid #667eea;';
            accessInfoContent = '<strong>✅ You can access:</strong> Products, Reviews, Categories<br><strong>❌ Need an account for:</strong> Orders, Cart, Shipping';
        } else if (CHAT_CONFIG.role === 'user') {
            accessInfoStyle = 'background: rgba(17, 153, 142, 0.2); border-left: 4px solid #11998e;';
            accessInfoContent = '<strong>✅ You can access:</strong> Your Orders, Your Shipments, Products, Reviews, Categories<br><strong>❌ Admin only:</strong> Other users\' data, Analytics, All orders';
        } else {
            accessInfoStyle = 'background: rgba(235, 51, 73, 0.2); border-left: 4px solid #eb3349;';
            accessInfoContent = '<strong>✅ Full Access:</strong> All Orders, All Users, All Products, Payments, Shipments, Inventory, Coupons, Reviews, Analytics, Events';
        }
        
        // Clear UI
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <h2>${CHAT_CONFIG.welcomeTitle}</h2>
                <p>${CHAT_CONFIG.welcomeMessage}</p>
                <div class="example-queries">
                    <p><strong>🎯 Try asking:</strong></p>
                    <ul>${examplesHtml}</ul>
                </div>
                <div class="access-info" style="margin-top: 20px; padding: 15px; ${accessInfoStyle} border-radius: 8px;">
                    <p style="margin: 0; font-size: 14px;">${accessInfoContent}</p>
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
