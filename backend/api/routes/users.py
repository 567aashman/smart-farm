"""
SmartFarm AI - Users API Routes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.schemas import UserCreate, UserUpdate, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user/farmer account."""
    if payload.email:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
    )
    if payload.password:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"])
        user.hashed_password = pwd_context.hash(payload.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"New user created: {user.id} ({user.name})")
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/notifications")
def get_notifications(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    from backend.models import Notification
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": n.id,
            "type": n.notification_type.value,
            "title": n.title,
            "message": n.message,
            "sent": n.sent,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]
