import cloudinary
import cloudinary.uploader
from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_image(file: UploadFile) -> str:
    """
    Upload an image to Cloudinary and return the URL.
    
    Args:
        file: The uploaded file object
    
    Returns:
        The URL of the uploaded image
    """
    # Read file content
    contents = await file.read()
    
    # Upload to Cloudinary
    upload_result = cloudinary.uploader.upload(contents)
    
    # Return the URL of the uploaded image
    return upload_result["secure_url"]