import os
import time
import httpx
import logging
from dotenv import load_dotenv

# Load dependencies for the full bot
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.database import SessionLocal
from backend.models import User
from backend.agents.ask_shyam import ask_shyam_agent
from backend.services.weather_service import weather_service

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from backend.config.settings import settings

TOKEN = settings.telegram_bot_token
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def send(chat_id, text, parse_mode="HTML"):
    try:
        r = httpx.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10
        )
        logger.info(f"Send result: {r.status_code} {r.text}")
        return r.json()
    except Exception as e:
        logger.error(f"Send failed: {e}")


def send_audio(chat_id, audio_file_path):
    try:
        with open(audio_file_path, "rb") as f:
            files = {"voice": f}
            data = {"chat_id": chat_id}
            r = httpx.post(
                f"{BASE_URL}/sendVoice",
                data=data,
                files=files,
                timeout=30
            )
            logger.info(f"Send audio result: {r.status_code} {r.text}")
            return r.json()
    except Exception as e:
        logger.error(f"Send audio failed: {e}")


def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        r = httpx.get(f"{BASE_URL}/getUpdates", params=params, timeout=40)
        return r.json().get("result", [])
    except Exception as e:
        logger.error(f"getUpdates failed: {e}")
        return []


def handle_start(db, chat_id, text):
    parts = text.split()
    if len(parts) > 1:
        code = parts[1].strip()
        from datetime import datetime
        user = db.query(User).filter(User.telegram_link_code == code).first()
        if user and user.telegram_link_expires and user.telegram_link_expires > datetime.utcnow():
            user.telegram_chat_id = str(chat_id)
            user.telegram_connected = True
            user.telegram_link_code = None
            user.telegram_link_expires = None
            db.commit()
            send(
                chat_id,
                f"✅ <b>Account linked successfully!</b>\n\n"
                f"Hello {user.name}! 🌾\n\n"
                f"You'll now receive updates. Ask me anything!"
            )
        else:
            send(chat_id, "❌ Invalid or expired linking code.")
    else:
        send(
            chat_id,
            "🌾 <b>Namaste!</b> SmartFarm app mein Connect Telegram button dabake code lein."
        )


def handle_status(db, chat_id):
    user = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if not user:
        send(chat_id, "⚠️ Your account is not linked yet. Use <code>/start CODE</code> to link.")
        return
    farm = user.farms[0] if user.farms else None
    if not farm:
        send(chat_id, "❌ No farm found. Please set up your farm in the dashboard.")
        return
    
    crop_count = len(farm.fields[0].crops) if farm.fields and farm.fields[0].crops else 0
    send(chat_id, f"📊 <b>Farm Status</b>\n\n<b>Farm Name:</b> {farm.name}\n<b>Active Crops:</b> {crop_count}")


def handle_today(db, chat_id):
    user = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if not user:
        send(chat_id, "⚠️ Your account is not linked yet.")
        return
    farm = user.farms[0] if user.farms else None
    if not farm:
        send(chat_id, "❌ No farm found.")
        return

    # Call AI or a service for today's plan
    send(chat_id, "⏳ Fetching your action plan for today...")
    try:
        import asyncio
        result = asyncio.run(ask_shyam_agent.chat(
            user_message="What is my action plan for today?",
            farm_id=farm.id,
            user_id=user.id,
            db=db,
            weather_service=weather_service
        ))
        send(chat_id, f"📝 <b>Today's Plan:</b>\n\n{result['reply']}")
    except Exception as e:
        logger.error(f"Failed to fetch today's plan: {e}")
        send(chat_id, "⚠️ Could not fetch action plan right now.")


def handle_help(chat_id):
    text = (
        "🛠️ <b>KisanSathi Bot Commands</b>\n\n"
        "/start <code> - Link your account\n"
        "/status - View your farm status\n"
        "/today - Get today's action plan\n"
        "/help - Show this list\n\n"
        "You can also chat directly with me for farming advice!"
    )
    send(chat_id, text)


def handle_chat(db, chat_id, text, is_voice=False, lang="hi"):
    user = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if not user:
        send(chat_id, "⚠️ Your account is not linked yet. Use <code>/start CODE</code>.")
        return
    farm = user.farms[0] if user.farms else None
    if not farm:
        send(chat_id, "❌ No farm found.")
        return

    send(chat_id, "🌱 Let me check...")
    try:
        import asyncio
        result = asyncio.run(ask_shyam_agent.chat(
            user_message=text,
            farm_id=farm.id,
            user_id=user.id,
            db=db,
            weather_service=weather_service
        ))
        
        reply_text = result['reply']
        send(chat_id, f"🤖 <b>KisanSathi:</b>\n\n{reply_text}")
        
        if is_voice:
            from gtts import gTTS
            import tempfile
            import os
            try:
                clean_text = reply_text.replace('*', '').replace('#', '').replace('_', '')
                tts = gTTS(text=clean_text, lang=lang)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tmp_path = tmp.name
                tts.save(tmp_path)
                send_audio(chat_id, tmp_path)
            except Exception as e:
                logger.error(f"TTS error: {e}")
            finally:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
    except Exception as e:
        logger.error(f"Ask Shyam chat error: {e}")
        send(chat_id, "⚠️ Sorry, Ask Shyam is temporarily unavailable.")


def handle_voice(db, chat_id, file_id):
    user = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if not user:
        send(chat_id, "⚠️ Your account is not linked yet. Use <code>/start CODE</code>.")
        return
        
    send(chat_id, "🎙️ Sun raha hoon... (Listening...)")
    
    try:
        r_file = httpx.get(f"{BASE_URL}/getFile", params={"file_id": file_id}, timeout=20)
        file_path = r_file.json().get("result", {}).get("file_path")
        if not file_path:
            send(chat_id, "❌ Audio download failed.")
            return
            
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        r_audio = httpx.get(download_url, timeout=30)
        if r_audio.status_code != 200:
            send(chat_id, "❌ Could not download audio.")
            return
            
        import tempfile
        import os
        from groq import Groq
        from backend.config.settings import settings
        
        groq_client = Groq(api_key=settings.groq_api_key)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            tmp.write(r_audio.content)
            tmp_path = tmp.name
            
        try:
            with open(tmp_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                  file=(os.path.basename(tmp_path), audio_file.read()),
                  model="whisper-large-v3",
                  response_format="verbose_json"
                )
            
            text = transcription.text
            lang = getattr(transcription, "language", "hi")
            
            if not text or not text.strip():
                send(chat_id, "🤷 Aawaz saaf nahi aayi. Kripya dobara bolen.")
                return
                
            send(chat_id, f"📝 <b>Aapne kaha:</b> <i>{text}</i>")
            
            # Feed to Ask Shyam
            handle_chat(db, chat_id, text, is_voice=True, lang=lang)
            
        finally:
            os.remove(tmp_path)
            
    except Exception as e:
        logger.error(f"Voice handling error: {e}")
        send(chat_id, "⚠️ Voice processing mein error aayi.")


def main():
    offset = None
    logger.info("=== BOT STARTED ===")
    
    while True:
        updates = get_updates(offset)
        
        for update in updates:
            offset = update["update_id"] + 1
            
            # Acknowledge immediately to prevent spam loop if there are crashes or duplicate bots
            try:
                httpx.get(f"{BASE_URL}/getUpdates", params={"offset": offset, "timeout": 0})
            except Exception:
                pass
                
            msg = update.get("message")
            
            if msg:
                chat_id = msg["chat"]["id"]
                
                db = SessionLocal()
                try:
                    if "text" in msg:
                        text = msg["text"].strip()
                        logger.info(f"Text Message from {chat_id}: {text}")
                        if text.startswith("/start"):
                            handle_start(db, chat_id, text)
                        elif text.startswith("/status"):
                            handle_status(db, chat_id)
                        elif text.startswith("/today"):
                            handle_today(db, chat_id)
                        elif text.startswith("/help"):
                            handle_help(chat_id)
                        else:
                            handle_chat(db, chat_id, text)
                    elif "voice" in msg:
                        file_id = msg["voice"]["file_id"]
                        logger.info(f"Voice Message from {chat_id}")
                        handle_voice(db, chat_id, file_id)
                finally:
                    db.close()
        
        time.sleep(1)


if __name__ == "__main__":
    main()
