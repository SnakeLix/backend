from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, UUID4

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    user_metadata: Optional[Dict[str, Any]] = {}

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    user_metadata: Optional[Dict[str, Any]] = None

class UserInDB(UserBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class User(UserInDB):
    pass

# Login schema
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: str
    exp: datetime

# Document schemas
class Page(BaseModel):
    image_url: str
    text: str
    
    class Config:
        from_attributes = True
        json_encoders = {
            # Add any custom encoders if needed
        }

class DocumentBase(BaseModel):
    title: Optional[str] = None
    data: Dict[str, Any] = {"pages": []}  # Using Dict[str, Any] instead of Dict[str, List[Page]]

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    data: Optional[Dict[str, Any]] = None  # Using Dict[str, Any] to store the pages

class DocumentInDB(DocumentBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Document(DocumentInDB):
    pass