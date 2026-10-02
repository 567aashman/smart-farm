import asyncio
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import User

def run_test():
    client = TestClient(app)
    
    # Create a test user
    db = SessionLocal()
    test_user = User(name="Test User", email="test_telegram@example.com")
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    user_id = test_user.id
    
    try:
        # 1. Call /link-code -> get code
        response = client.post(f"/api/telegram/link-code?user_id={user_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "code" in data
        code = data["code"]
        print(f"Generated Code: {code}")
        
        # Verify db
        db.refresh(test_user)
        print(f"DB user code: {test_user.telegram_link_code}, Expires: {test_user.telegram_link_expires}")
        assert test_user.telegram_link_code == code
        
        # 2. Simulate /start <code> in the bot handler
        update_payload = {
            "message": {
                "chat": {"id": 123456789},
                "text": f"/start {code}"
            }
        }
        response = client.post("/api/telegram/webhook", json=update_payload)
        assert response.status_code == 200
        
        # Verify db directly
        db.refresh(test_user)
        print(f"DB user connected: {test_user.telegram_connected}, chat_id: {test_user.telegram_chat_id}")
        assert test_user.telegram_connected is True
        assert test_user.telegram_chat_id == "123456789"
        
        # 3. Call /status -> must return {"connected": true}
        response = client.get(f"/api/telegram/status?user_id={user_id}")
        assert response.status_code == 200
        status_data = response.json()
        print(f"Status endpoint response: {status_data}")
        assert status_data["connected"] is True
        
        print("✅ Telegram linking flow test passed successfully!")
    finally:
        db.delete(test_user)
        db.commit()
        db.close()

if __name__ == "__main__":
    run_test()
