import os
import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
print(f"Token loaded: {'YES' if token else 'NO'}")
print(f"Token preview: {token[:10]}..." if token else "NO TOKEN")

# Delete webhook to prevent conflicts
r3 = httpx.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
print(f"deleteWebhook: {r3.json()}")

# Test 1: getMe
r = httpx.get(f"https://api.telegram.org/bot{token}/getMe")
print(f"getMe status: {r.status_code}")
print(f"getMe response: {r.json()}")

# Test 2: getUpdates
r2 = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates")
print(f"getUpdates status: {r2.status_code}")
print(f"getUpdates response: {r2.json()}")
