#!/usr/bin/env python
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import our app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.database import Base
from app.models.models import User, Document
from app.utils.security import get_password_hash

def init_db():
    """Initialize the database with initial data"""
    settings = get_settings()
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if we already have users
        user_count = db.query(User).count()
        
        if user_count == 0:
            print("Creating initial admin user...")
            
            # Create admin user
            admin_user = User(
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                user_metadata={"is_admin": True}  # Changed from metadata to user_metadata
            )
            
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            print(f"Admin user created with ID: {admin_user.id}")
            
            # Create sample document
            sample_doc = Document(
                user_id=admin_user.id,
                title="Sample Document",
                data={"pages": [{"image_url": "https://placeholder.com/image.jpg", "text": "This is a sample document page"}]}
            )
            
            db.add(sample_doc)
            db.commit()
            
            print("Sample document created")
        else:
            print("Database already contains users, skipping initialization")
            
    except Exception as e:
        print(f"Error during database initialization: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing the database...")
    init_db()
    print("Database initialization completed")