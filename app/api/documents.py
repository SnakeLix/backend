from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User, Document
from app.schemas import Document as DocumentSchema, DocumentCreate, DocumentUpdate
from app.utils.cloudinary import upload_image

router = APIRouter()

@router.get("/documents", response_model=List[DocumentSchema], tags=["documents"])
def read_documents(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Retrieve current user's documents
    """
    documents = db.query(Document).filter(
        Document.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return documents

@router.post("/documents", response_model=DocumentSchema, tags=["documents"])
def create_document(
    *,
    request: Request,
    db: Session = Depends(get_db),
    document_in: DocumentCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create new document
    """
    document = Document(
        user_id=current_user.id,
        title=document_in.title,
        data=document_in.data
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

@router.post("/upload-image", tags=["documents"])
async def upload_document_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Upload an image to Cloudinary and return the image URL
    This URL can be used in the document data.pages array
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    image_url = await upload_image(file)
    return {"image_url": image_url}

@router.get("/documents/{document_id}", response_model=DocumentSchema, tags=["documents"])
def read_document(
    *,
    request: Request,
    db: Session = Depends(get_db),
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get specific document by id
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document

@router.put("/documents/{document_id}", response_model=DocumentSchema, tags=["documents"])
def update_document(
    *,
    request: Request,
    db: Session = Depends(get_db),
    document_id: UUID,
    document_in: DocumentUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update document
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document_in.title is not None:
        document.title = document_in.title
    if document_in.data is not None:
        document.data = document_in.data
    
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

@router.delete("/documents/{document_id}", response_model=DocumentSchema, tags=["documents"])
def delete_document(
    *,
    request: Request,
    db: Session = Depends(get_db),
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete document
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    db.delete(document)
    db.commit()
    return document