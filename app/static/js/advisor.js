// AI Advisor Interactive Chat Client

document.addEventListener('DOMContentLoaded', function () {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const sendBtn = document.getElementById('sendChatBtn');

    if (!chatForm || !chatInput || !chatMessages) {
        return;
    }

    // Scroll to bottom on load
    scrollChatToBottom();

    // Handle form submit
    chatForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;

        sendMessage(message);
    });

    // Quick prompt buttons
    document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const promptText = this.getAttribute('data-prompt');
            if (promptText) {
                chatInput.value = promptText;
                sendMessage(promptText);
            }
        });
    });

    function sendMessage(text) {
        // Append user bubble
        appendMessage('user', text);
        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // Show typing indicator
        const typingIndicator = showTypingIndicator();

        fetch('/advisor/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ message: text })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            removeTypingIndicator(typingIndicator);
            appendMessage('assistant', data.reply);
        })
        .catch(err => {
            removeTypingIndicator(typingIndicator);
            appendMessage('assistant', 'Sorry, I encountered an issue generating a response. Please verify your settings or try again.');
            console.error('Chat error:', err);
        })
        .finally(() => {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
            scrollChatToBottom();
        });
    }

    function appendMessage(role, text) {
        const bubble = document.createElement('div');
        bubble.classList.add('chat-bubble', role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant');

        // Simple markdown bullet conversion
        let formattedText = escapeHtml(text)
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');

        bubble.innerHTML = formattedText;
        chatMessages.appendChild(bubble);
        scrollChatToBottom();
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.classList.add('chat-bubble', 'chat-bubble-assistant', 'text-muted', 'typing-indicator');
        indicator.innerHTML = '<i class="bi bi-three-dots fs-5"></i> <em>FinBot is thinking...</em>';
        chatMessages.appendChild(indicator);
        scrollChatToBottom();
        return indicator;
    }

    function removeTypingIndicator(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
    }

    function scrollChatToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }
});
