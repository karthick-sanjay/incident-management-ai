from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserOut
from backend.app.services.auth_service import get_current_user, RoleChecker

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("", response_model=List[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Restrict to admin only
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User management access limited to administrators."
        )
    return db.query(User).order_by(User.created_at.desc()).all()

@router.get("/engineers", response_model=List[UserOut])
def get_engineers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Support, DevOps, and Admins can query target assignees list
    return db.query(User).filter(User.role.in_(["support_engineer", "devops_engineer"])).all()

@router.put("/{id}/role", response_model=UserOut)
def update_user_role(
    id: uuid.UUID,
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    if role not in ["admin", "support_engineer", "devops_engineer"]:
        raise HTTPException(status_code=400, detail="Invalid role type specified")
        
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = role
    db.commit()
    db.refresh(user)
    
    return user
