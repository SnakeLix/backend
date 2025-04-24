from fastapi import Depends, HTTPException, status, Header, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional, Annotated

from app.database import get_db
from app.models import User
from app.schemas import TokenPayload
from app.config import get_settings

settings = get_settings()

# Security scheme for Swagger UI with custom scheme name
auth_bearer = HTTPBearer(scheme_name='Authorization')

def get_bearer_token(request: Request) -> str:
    """
    Extract bearer token from request headers
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth.replace("Bearer ", "")

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(auth_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate access token and return current user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Get token from credentials
        token = credentials.credentials
            
        # Decode JWT token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (JWTError, AttributeError):
        # Try to get token from request directly as fallback
        try:
            token = get_bearer_token(request)
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user