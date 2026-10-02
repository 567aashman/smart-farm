import os
import time
import httpx
from dotenv import load_dotenv

# Load env variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env file!")
    exit(1)

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
LOCAL_WEBHOOK_URL = "http://localhost:8000/api/telegram/webhook"

def run_forwarder():
    print("[INFO] Starting Local Telegram Bot Forwarder...")
    
    # 1. Delete any existing webhook so we can use getUpdates
    with httpx.Client() as client:
        res = client.get(f"{TELEGRAM_API}/deleteWebhook")
        if res.status_code == 200:
            print("[SUCCESS] Webhook cleared, switching to local polling mode.")
        else:
            print("[WARNING] Failed to clear webhook:", res.text)
            
    print(f"[INFO] Listening for Telegram messages and forwarding to {LOCAL_WEBHOOK_URL}...")
    
    offset = None
    with httpx.Client(timeout=30) as client:
        while True:
            try:
                # Get updates from Telegram
                params = {"timeout": 10}
                if offset:
                    params["offset"] = offset
                
                res = client.get(f"{TELEGRAM_API}/getUpdates", params=params)
                if res.status_code == 200:
                    data = res.json()
                    if not data.get("ok"):
                        continue
                        
                    updates = data.get("result", [])
                    for update in updates:
                        # Forward each update to our local FastAPI webhook
                        try:
                            fwd_res = client.post(LOCAL_WEBHOOK_URL, json=update)
                            if fwd_res.status_code == 200:
                                print(f"[SUCCESS] Forwarded message from {update.get('message', {}).get('chat', {}).get('id')} to local backend.")
                            else:
                                print(f"[ERROR] Backend returned error {fwd_res.status_code}. Is Uvicorn running on port 8000?")
                        except Exception as e:
                            print(f"[ERROR] Failed to reach local backend (Is uvicorn running?): {e}")
                            
                        # Update offset to acknowledge message
                        offset = update["update_id"] + 1
                
            except Exception as e:
                print(f"[WARNING] Polling error: {e}")
                time.sleep(2)

if __name__ == "__main__":
    run_forwarder()
