import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend.models.models import (
    User, Farm, Field, Crop, CropStage, 
    IrrigationRecord, FarmTask, WeatherRecord, 
    SoilProfile, Notification
)

def clear_test_data():
    db = SessionLocal()
    try:
        print("Clearing test data...")
        # Delete data from all user-related tables
        db.query(Notification).delete()
        db.query(WeatherRecord).delete()
        db.query(FarmTask).delete()
        db.query(IrrigationRecord).delete()
        db.query(CropStage).delete()
        db.query(Crop).delete()
        db.query(Field).delete()
        db.query(SoilProfile).delete()
        db.query(Farm).delete()
        db.query(User).delete()
        
        db.commit()
        print("✅ Saara random test data database se delete ho gaya hai! (Crop catalog waise ka waisa hai).")
    except Exception as e:
        db.rollback()
        print(f"❌ Error aaya: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_test_data()
