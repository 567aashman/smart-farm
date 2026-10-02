/**
 * SmartFarm AI - FarmAI Chat JS
 */

if (!requireAuth()) { /* redirected */ }

document.getElementById('sb-farm-name').textContent = State.farmName;
document.getElementById('sb-user-name').textContent = State.userName;

const farmId = State.farmId;
const userId = State.userId;
let conversationHistory = [];
let isTyping = false;

// ── Send Message ──
async function sendMessage() {
  if (isTyping) return;
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  input.style.height = '42px';
  document.getElementById('suggestions').style.display = 'none';

  appendMessage('user', message);
  showTyping();

  isTyping = true;
  document.getElementById('chat-send').disabled = true;

  try {
    const result = await API.chatWithAI(userId, farmId, message, conversationHistory);

    removeTyping();
    appendBotMessage(result.reply, result.tools_used || []);

    // Update history
    conversationHistory.push({ role: 'user', content: message });
    conversationHistory.push({ role: 'assistant', content: result.reply });
    if (conversationHistory.length > 20) conversationHistory = conversationHistory.slice(-20);

  } catch (e) {
    removeTyping();
    appendBotMessage(
      `⚠️ FarmAI is temporarily unavailable.\n\n${e.message}\n\nPlease check that:\n• GROQ_API_KEY is set in .env\n• The backend is running`,
      []
    );
  } finally {
    isTyping = false;
    document.getElementById('chat-send').disabled = false;
    input.focus();
  }
}

function appendMessage(role, text) {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  div.innerHTML = `
    <div class="message-avatar ${role}">${role === 'user' ? '👤' : '🌾'}</div>
    <div>
      <div class="message-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
    </div>
  `;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function appendBotMessage(text, toolsUsed) {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-message bot';

  const toolsHtml = toolsUsed.length > 0 ? `
    <div class="message-tools">
      ${toolsUsed.map(t => `<span class="tool-chip">🔧 ${t.replace(/_/g, ' ')}</span>`).join('')}
    </div>
  ` : '';

  div.innerHTML = `
    <div class="message-avatar bot">🌾</div>
    <div>
      <div class="message-bubble">${formatBotText(text)}</div>
      ${toolsHtml}
    </div>
  `;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function showTyping() {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-message bot';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="message-avatar bot">🌾</div>
    <div>
      <div class="message-bubble" style="padding:8px 14px">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>
  `;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function formatBotText(text) {
  return escapeHtml(text)
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function clearChat() {
  conversationHistory = [];
  document.getElementById('chat-messages').innerHTML = `
    <div class="chat-message bot">
      <div class="message-avatar bot">🌾</div>
      <div>
        <div class="message-bubble">Chat cleared. How can I help you today? 🌾</div>
      </div>
    </div>
  `;
  document.getElementById('suggestions').style.display = 'block';
}

function sendSuggestion(btn) {
  document.getElementById('chat-input').value = btn.textContent;
  sendMessage();
}

// ── Auto-resize textarea ──
document.getElementById('chat-input').addEventListener('input', function () {
  this.style.height = '42px';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

document.getElementById('chat-input').addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
