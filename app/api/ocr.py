from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import numpy as np
import cv2
import requests
import base64
from io import BytesIO
from PIL import Image


from app.module.inference import run_ocr_on_image_path, run_ocr_on_image_array
import tempfile

router = APIRouter()

class OCRUrlRequest(BaseModel):
    url: HttpUrl

class OCRBase64Request(BaseModel):
    base64_image: str

@router.post("/ocr/file", summary="OCR from image file", tags=["ocr"])
async def ocr_from_file(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        result = run_ocr_on_image_path(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")
    finally:
        import os
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
    return JSONResponse(content=result)

@router.post("/ocr/url", summary="OCR from image URL", tags=["ocr"])
async def ocr_from_url(payload: OCRUrlRequest):
    try:
        response = requests.get(str(payload.url), timeout=10)
        response.raise_for_status()
        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from URL.")
        result = run_ocr_on_image_array(img)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image from URL: {str(e)}")
    return JSONResponse(content=result)


def preprocess_base64_image(base64_string: str) -> np.ndarray:
    """
    Decode base64 string to image array (BGR format).
    """
    try:
        # Remove any potential whitespace or newlines
        base64_string = base64_string.strip()
        
        # Check if the string is empty
        if not base64_string:
            raise ValueError("Empty base64 string received")
        
        # Handle data URI prefixes
        if base64_string.startswith('data:'):
            # Extract the base64 part
            _, base64_string = base64_string.split(',', 1)
        
        # Add padding if needed
        padding = 4 - (len(base64_string) % 4) if len(base64_string) % 4 else 0
        base64_string += '=' * padding
        
        # Decode the base64 string into bytes
        try:
            img_data = base64.b64decode(base64_string)
        except Exception as e:
            # Try to clean the string further (remove non-base64 characters)
            import re
            base64_string = re.sub(r'[^A-Za-z0-9+/=]', '', base64_string)
            img_data = base64.b64decode(base64_string)
        
        # Debug info about the received data
        print(f"Decoded base64 data length: {len(img_data)} bytes")
        
        # Try PIL first, which is more robust for different image formats
        try:
            pil_img = Image.open(BytesIO(img_data))
            print(f"PIL decoded image format: {pil_img.format}, size: {pil_img.size}, mode: {pil_img.mode}")
            
            # Convert PIL image to numpy array
            img = np.array(pil_img)
            
            # Convert to BGR for OpenCV compatibility
            if len(img.shape) == 3:
                if img.shape[2] == 3:  # RGB
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                elif img.shape[2] == 4:  # RGBA
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            
            return img
            
        except Exception as pil_error:
            print(f"PIL decoding failed: {pil_error}, trying OpenCV")
            
            # Fallback to OpenCV method
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None or img.size == 0:
                # Try to save the raw data to a temporary file and load it
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp.write(img_data)
                    tmp_path = tmp.name
                    
                try:
                    img = cv2.imread(tmp_path)
                    if img is not None and img.size > 0:
                        print(f"Successfully loaded from temp file: {img.shape}")
                    else:
                        raise ValueError("Failed to load image from temp file")
                finally:
                    import os
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            
            if img is None or img.size == 0:
                raise ValueError("Failed to decode image with both PIL and OpenCV methods")
                
            return img
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Base64 image processing error: {str(e)}\n{error_details}")
        raise ValueError(f"Image processing error: {str(e)}")

@router.post("/ocr/base64", summary="OCR from base64 image", tags=["ocr"])
async def ocr_from_base64(payload: OCRBase64Request):
    try:
        # Get the base64 string
        base64_str = payload.base64_image
        
        # Log the string length for debugging
        print(f"Received base64 string length: {len(base64_str)}")
        
        # Sample the start of the string to check format (don't log the whole thing)
        sample = base64_str[:30] + "..." if len(base64_str) > 30 else base64_str
        print(f"Sample of received base64: {sample}")
        
        # Process the image
        img = preprocess_base64_image(base64_str)
        
        # Log information about the processed image
        if img is not None:
            print(f"Processed image shape: {img.shape}, dtype: {img.dtype}")
        
        # Run OCR
        result = run_ocr_on_image_array(img)
        return JSONResponse(content=result)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"OCR base64 error: {str(e)}\n{error_details}")
        raise HTTPException(status_code=400, detail=f"Failed to process base64 image: {str(e)}")
