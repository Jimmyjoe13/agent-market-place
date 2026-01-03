/**
 * RAG Assistant Widget SDK
 * =========================
 * 
 * Script à intégrer sur les sites clients pour afficher le chatbot.
 * Configuration via window.RAGAssistantConfig.
 */

(function() {
    // Configuration par défaut
    const config = window.RAGAssistantConfig || {};
    const API_URL = config.apiUrl || 'http://localhost:8000';
    const AGENT_ID = config.agentId;
    const THEME_COLOR = config.themeColor || '#4F46E5';
    const POSITION = config.position || 'bottom-right';

    if (!AGENT_ID) {
        console.error('RAG Assistant: Agent ID missing configuration.');
        return;
    }

    // Styles CSS
    const styles = `
        .rag-assistant-widget {
            position: fixed;
            z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            bottom: 20px;
            right: 20px;
        }
        
        .rag-assistant-widget.position-bottom-left {
            right: auto;
            left: 20px;
        }

        .rag-assistant-toggle {
            width: 60px;
            height: 60px;
            border-radius: 30px;
            background-color: ${THEME_COLOR};
            color: white;
            border: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s;
        }

        .rag-assistant-toggle:hover {
            transform: scale(1.05);
        }

        .rag-assistant-toggle svg {
            width: 32px;
            height: 32px;
        }

        .rag-assistant-window {
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 380px;
            height: 600px;
            max-height: calc(100vh - 100px);
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            display: none;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid #e5e7eb;
        }

        .rag-assistant-widget.position-bottom-left .rag-assistant-window {
            right: auto;
            left: 0;
        }

        .rag-assistant-window.open {
            display: flex;
        }

        .rag-assistant-header {
            background-color: ${THEME_COLOR};
            color: white;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .rag-assistant-header h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
        }

        .rag-assistant-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            background-color: #f9fafb;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .rag-message {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.5;
        }

        .rag-message.user {
            background-color: ${THEME_COLOR};
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 2px;
        }

        .rag-message.agent {
            background-color: white;
            color: #1f2937;
            align-self: flex-start;
            border-bottom-left-radius: 2px;
            border: 1px solid #e5e7eb;
        }

        .rag-assistant-input {
            padding: 16px;
            border-top: 1px solid #e5e7eb;
            background: white;
            display: flex;
            gap: 8px;
        }

        .rag-assistant-input input {
            flex: 1;
            padding: 10px 14px;
            border: 1px solid #d1d5db;
            border-radius: 20px;
            outline: none;
            font-size: 14px;
        }

        .rag-assistant-input input:focus {
            border-color: ${THEME_COLOR};
        }

        .rag-assistant-input button {
            background-color: ${THEME_COLOR};
            color: white;
            border: none;
            border-radius: 20px;
            padding: 6px 16px;
            cursor: pointer;
            font-weight: 500;
        }

        .rag-assistant-input button:disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }

        /* Loading Dots */
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 4px 8px;
        }
        .typing-dot {
            width: 6px;
            height: 6px;
            background: #9ca3af;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    `;

    // Injecter les styles
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);

    // Créer le widget
    const widget = document.createElement('div');
    widget.className = `rag-assistant-widget position-${POSITION}`;
    
    widget.innerHTML = `
        <button class="rag-assistant-toggle">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
        </button>
        <div class="rag-assistant-window">
            <div class="rag-assistant-header">
                <h3>${config.title || 'Assistant IA'}</h3>
                <div style="cursor:pointer" onclick="document.querySelector('.rag-assistant-window').classList.remove('open')">✕</div>
            </div>
            <div class="rag-assistant-messages">
                <div class="rag-message agent">
                    Bonjour ! Comment puis-je vous aider aujourd'hui ?
                </div>
            </div>
            <form class="rag-assistant-input">
                <input type="text" placeholder="Posez votre question..." required>
                <button type="submit">Envoyer</button>
            </form>
        </div>
    `;

    document.body.appendChild(widget);

    // Event Listeners
    const toggleBtn = widget.querySelector('.rag-assistant-toggle');
    const windowEl = widget.querySelector('.rag-assistant-window');
    const form = widget.querySelector('form');
    const input = widget.querySelector('input');
    const messagesEl = widget.querySelector('.rag-assistant-messages');

    let isOpen = false;
    let sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

    toggleBtn.addEventListener('click', () => {
        isOpen = !isOpen;
        if (isOpen) {
            windowEl.classList.add('open');
            input.focus();
        } else {
            windowEl.classList.remove('open');
        }
    });

    const addMessage = (text, type) => {
        const div = document.createElement('div');
        div.className = `rag-message ${type}`;
        div.innerText = text;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    };

    const addTyping = () => {
        const div = document.createElement('div');
        div.className = 'rag-message agent typing-indicator';
        div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    };

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (!query) return;

        // User message
        addMessage(query, 'user');
        input.value = '';
        input.disabled = true;

        // Loading
        const typingEl = addTyping();

        try {
            const response = await fetch(`${API_URL}/api/v1/assistant-plugin/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Agent-ID': AGENT_ID
                },
                body: JSON.stringify({
                    query: query,
                    session_id: sessionId
                })
            });

            const data = await response.json();
            
            // Remove typing
            typingEl.remove();

            if (data.response) {
                addMessage(data.response, 'agent');
            } else {
                addMessage("Désolé, je n'ai pas compris.", 'agent');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            typingEl.remove();
            addMessage("Une erreur est survenue. Veuillez réessayer.", 'agent');
        } finally {
            input.disabled = false;
            input.focus();
        }
    });

})();
