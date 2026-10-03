document.addEventListener("DOMContentLoaded", () => {
    // Inject CSS
    const style = document.createElement("style");
    style.innerHTML = `
        /* Ask Shyam Widget Styles */
        .shyam-widget-btn {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 70px;
            height: 70px;
            border-radius: 35px;
            background-color: var(--color-primary);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            cursor: pointer;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            animation: bounceIn 0.8s ease;
        }
        .shyam-widget-btn:hover {
            transform: scale(1.08);
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }
        .shyam-widget-avatar {
            width: 62px;
            height: 62px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid white;
        }
        
        .shyam-chat-popup {
            position: fixed;
            bottom: 110px;
            right: 24px;
            width: 380px;
            height: 550px;
            max-height: calc(100vh - 140px);
            background: var(--color-surface);
            border-radius: 16px;
            box-shadow: 0 12px 28px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            z-index: 9998;
            overflow: hidden;
            transform: translateY(30px);
            opacity: 0;
            pointer-events: none;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.3s ease;
        }
        
        .shyam-chat-popup.open {
            transform: translateY(0);
            opacity: 1;
            pointer-events: auto;
        }
        
        .shyam-chat-header {
            background: var(--color-primary);
            color: white;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .shyam-chat-header img {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid rgba(255,255,255,0.6);
            object-fit: cover;
        }
        .shyam-chat-header-info {
            flex-grow: 1;
        }
        .shyam-chat-header-title {
            font-weight: 700;
            font-size: 1.1rem;
            margin: 0;
            line-height: 1.2;
        }
        .shyam-chat-header-subtitle {
            font-size: 0.8rem;
            opacity: 0.9;
        }
        .shyam-chat-close {
            background: none;
            border: none;
            color: white;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 4px;
        }
        
        .shyam-chat-body {
            flex-grow: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
            background-color: var(--color-background);
        }
        
        .shyam-msg {
            max-width: 85%;
            padding: 12px 16px;
            border-radius: 16px;
            font-size: 0.95rem;
            line-height: 1.4;
            animation: fadeIn 0.3s ease;
        }
        .shyam-msg.bot {
            background-color: var(--color-surface);
            border: 1px solid var(--color-border);
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .shyam-msg.user {
            background-color: var(--color-primary);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        
        .shyam-chat-footer {
            padding: 14px;
            background: var(--color-surface);
            border-top: 1px solid var(--color-border);
            display: flex;
            gap: 10px;
        }
        .shyam-chat-input {
            flex-grow: 1;
            border: 1px solid var(--color-border);
            border-radius: 20px;
            padding: 10px 16px;
            outline: none;
            font-size: 0.95rem;
        }
        .shyam-chat-input:focus {
            border-color: var(--color-primary);
        }
        .shyam-chat-send {
            background: var(--color-primary);
            color: white;
            border: none;
            width: 42px;
            height: 42px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }
        .shyam-chat-send:hover {
            opacity: 0.9;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes bounceIn {
            0% { transform: scale(0); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        @media (max-width: 768px) {
            .shyam-chat-popup {
                bottom: 0;
                right: 0;
                width: 100%;
                height: 100%;
                max-height: 100vh;
                border-radius: 0;
            }
            .shyam-widget-btn {
                bottom: 16px;
                right: 16px;
                width: 60px;
                height: 60px;
            }
            .shyam-widget-avatar {
                width: 52px;
                height: 52px;
            }
        }
    `;
    document.head.appendChild(style);

    // Inject HTML
    const widgetContainer = document.createElement("div");
    widgetContainer.innerHTML = `
        <div class="shyam-chat-popup" id="shyamChatPopup">
            <div class="shyam-chat-header">
                <img src="img/ask_shyam.jpg" alt="Ask Shyam">
                <div class="shyam-chat-header-info">
                    <div class="shyam-chat-header-title">Ask Shyam</div>
                    <div class="shyam-chat-header-subtitle">Your AI Farming Expert</div>
                </div>
                <button class="shyam-chat-close" id="shyamCloseBtn">✕</button>
            </div>
            <div class="shyam-chat-body" id="shyamChatBody">
                <div class="shyam-msg bot">
                    Namaste! 🙏 I am Shyam. Ask me anything about your farm, weather, or crops!
                </div>
            </div>
            <div id="shyamImagePreviewContainer" style="display:none; padding:0 14px 10px 14px; background:var(--color-surface); position:relative;">
                <img id="shyamImagePreview" src="" style="max-height:80px; border-radius:8px; border:1px solid var(--color-border);">
                <button id="shyamImageClearBtn" style="position:absolute; top:-5px; left:5px; background:red; color:white; border:none; border-radius:50%; width:20px; height:20px; cursor:pointer; font-size:12px;">✕</button>
            </div>
            <div class="shyam-chat-footer">
                <input type="file" id="shyamImageUpload" accept="image/*" style="display:none;">
                <button id="shyamAttachBtn" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--color-text-muted);" title="Upload Image">📷</button>
                <button id="shyamMicBtn" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--color-text-muted);" title="Voice Input">🎤</button>
                <input type="text" class="shyam-chat-input" id="shyamInput" placeholder="Type or speak here...">
                <button class="shyam-chat-send" id="shyamSendBtn">➤</button>
            </div>
        </div>
        
        <div class="shyam-widget-btn" id="shyamWidgetBtn" title="Ask Shyam">
            <img src="img/ask_shyam.jpg" class="shyam-widget-avatar" alt="Ask Shyam">
        </div>
    `;
    document.body.appendChild(widgetContainer);

    // Logic
    const widgetBtn = document.getElementById("shyamWidgetBtn");
    const popup = document.getElementById("shyamChatPopup");
    const closeBtn = document.getElementById("shyamCloseBtn");
    const input = document.getElementById("shyamInput");
    const sendBtn = document.getElementById("shyamSendBtn");
    const chatBody = document.getElementById("shyamChatBody");
    
    
    const attachBtn = document.getElementById("shyamAttachBtn");
    const imageUpload = document.getElementById("shyamImageUpload");
    const previewContainer = document.getElementById("shyamImagePreviewContainer");
    const previewImg = document.getElementById("shyamImagePreview");
    const clearBtn = document.getElementById("shyamImageClearBtn");
    
    let currentImageBase64 = null;

    attachBtn.addEventListener("click", () => imageUpload.click());
    
    imageUpload.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            currentImageBase64 = ev.target.result; // contains 'data:image/...;base64,...'
            previewImg.src = currentImageBase64;
            previewContainer.style.display = "block";
        };
        reader.readAsDataURL(file);
    });
    
    clearBtn.addEventListener("click", () => {
        currentImageBase64 = null;
        imageUpload.value = "";
        previewContainer.style.display = "none";
    });

    
    const micBtn = document.getElementById("shyamMicBtn");
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let currentVoiceBase64 = null;
    
    micBtn.addEventListener("click", async () => {
        if (isRecording) {
            mediaRecorder.stop();
            micBtn.style.color = "var(--color-text-muted)";
            micBtn.textContent = "🎤";
            isRecording = false;
        } else {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.addEventListener("dataavailable", event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener("stop", () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const reader = new FileReader();
                    reader.onload = () => {
                        currentVoiceBase64 = reader.result.split(',')[1];
                        // Auto-send when recording stops
                        handleSend();
                    };
                    reader.readAsDataURL(audioBlob);
                    
                    // Stop tracks
                    stream.getTracks().forEach(track => track.stop());
                });
                
                mediaRecorder.start();
                micBtn.style.color = "red";
                micBtn.textContent = "⏹️";
                isRecording = true;
            } catch (err) {
                alert("Microphone access denied or unavailable.");
            }
        }
    });

    let chatHistory = [];
    let visualHistory = [];
    
    // Load from local storage
    try {
        const storedApi = localStorage.getItem("shyamChatHistoryApi");
        const storedVisual = localStorage.getItem("shyamChatHistoryVisual");
        if (storedApi && storedVisual) {
            chatHistory = JSON.parse(storedApi);
            visualHistory = JSON.parse(storedVisual);
            
            if (visualHistory.length > 0) {
                chatBody.innerHTML = "";
                visualHistory.forEach(item => {
                    const msgDiv = document.createElement("div");
                    msgDiv.className = 'shyam-msg ' + item.sender;
                    msgDiv.innerHTML = item.html;
                    chatBody.appendChild(msgDiv);
                });
                chatBody.scrollTop = chatBody.scrollHeight;
            }
        }
    } catch(e) {}
    
    function saveHistory() {
        localStorage.setItem("shyamChatHistoryApi", JSON.stringify(chatHistory));
        localStorage.setItem("shyamChatHistoryVisual", JSON.stringify(visualHistory));
    }

    function toggleChat() {
        popup.classList.toggle("open");
        if (popup.classList.contains("open")) {
            input.focus();
        }
    }

    widgetBtn.addEventListener("click", toggleChat);
    closeBtn.addEventListener("click", toggleChat);

    function addMessage(text, sender, skipSave = false) {
        const msgDiv = document.createElement("div");
        msgDiv.className = 'shyam-msg ' + sender;
        
        let formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
            
        msgDiv.innerHTML = formattedText;
        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
        
        if (!skipSave) {
            visualHistory.push({ sender: sender, html: formattedText });
            saveHistory();
        }
    }

    async function handleSend() {
        const text = input.value.trim();
        if (!text && !currentVoiceBase64) return;
        
        if (!State.isLoggedIn()) {
            addMessage("Please log in to use Ask Shyam.", "bot", true);
            return;
        }

        
        let msgHtml = text || "🎤 <i>Voice Note</i>";
        if (currentImageBase64) {
            msgHtml = `<img src="${currentImageBase64}" style="max-width:100%; border-radius:8px; margin-bottom:8px; display:block;"><br>` + msgHtml;
        }
        addMessage(msgHtml, "user");

        input.value = "";
        
        const loadingId = "load-" + Date.now();
        const loadingDiv = document.createElement("div");
        loadingDiv.className = "shyam-msg bot";
        loadingDiv.id = loadingId;
        loadingDiv.innerHTML = '<span style="opacity:0.6">Thinking...</span>';
        chatBody.appendChild(loadingDiv);
        chatBody.scrollTop = chatBody.scrollHeight;

        try {
            
            // Only send the base64 part, not the prefix for the API (backend adds it if needed, or we just send it as is)
            const b64Data = currentImageBase64 ? currentImageBase64.split(',')[1] : null;
            
            const data = await API.chatWithAI(State.userId, State.farmId, text, chatHistory, b64Data, currentVoiceBase64);
            currentVoiceBase64 = null; // Reset
            
            // Play audio if generated
            if (data.audio_base64) {
                const audio = new Audio("data:audio/mp3;base64," + data.audio_base64);
                audio.play().catch(e => console.log("Audio play blocked by browser", e));
            }

            
            // Clear image after sending
            if (currentImageBase64) {
                clearBtn.click();
            }

            document.getElementById(loadingId).remove();
            
            chatHistory.push({ role: "user", content: text });
            chatHistory.push({ role: "assistant", content: data.reply });
            saveHistory();
            
            addMessage(data.reply, "bot");
        } catch (e) {
            document.getElementById(loadingId).remove();
            addMessage("⚠️ Sorry, I could not fetch an answer right now.", "bot", true);
        }
    }

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleSend();
    });
});
