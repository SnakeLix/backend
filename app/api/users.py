from datetime import timedelta
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body, Form, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import User 
from app.schemas import User as UserSchema, UserCreate, UserUpdate, Token, LoginRequest
from app.utils.security import verify_password, get_password_hash, create_access_token

settings = get_settings()
router = APIRouter()

@router.post("/token", response_model=Token, tags=["authentication"])
async def login_for_access_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Token endpoint, get an access token for future requests
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/users", response_model=UserSchema, tags=["users"])
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate
) -> Any:
    """
    Create new user
    """
    # Check if user with this email exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        user_metadata=user_in.user_metadata
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/users/me", response_model=UserSchema, tags=["users"])
def read_user_me(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user
    """
    return current_user

@router.put("/users/me", response_model=UserSchema, tags=["users"])
def update_user_me(
    *,
    request: Request,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update own user
    """
    if user_in.email is not None:
        current_user.email = user_in.email
    if user_in.password is not None:
        current_user.password_hash = get_password_hash(user_in.password)
    if user_in.user_metadata is not None:
        current_user.user_metadata = user_in.user_metadata
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/users", response_model=List[UserSchema], tags=["users"])
def read_users(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Retrieve users
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users