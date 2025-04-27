from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, List, Optional
import json

from app.api import users, documents, ocr
from app.config import get_settings
from app.api.deps import get_current_user
from app.utils.websocket import manager

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=None,  # Disable default Swagger UI
)

# Set up CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(ocr.router, prefix=settings.API_V1_STR)

# WebSocket endpoint for document notifications
@app.websocket("/ws/documents")
async def websocket_document_endpoint(
    websocket: WebSocket, 
    token: str = Query(...),
):
    from jose import jwt, JWTError
    from app.database import get_db
    from app.models import User
    from sqlalchemy.orm import Session
    
    # Get DB session
    db = next(get_db())
    
    # Validate JWT token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            await websocket.close(code=1008, reason="User not found")
            return
            
        # Accept connection
        await manager.connect(websocket, user_id)
        
        try:
            # Send connection confirmation
            await websocket.send_text(json.dumps({"status": "connected", "message": "WebSocket connection established"}))
            
            # Listen for messages
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    # Handle client messages here if needed
                    await websocket.send_text(json.dumps({"status": "received", "message": "Message received"}))
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"status": "error", "message": "Invalid JSON"}))
                    
        except WebSocketDisconnect:
            await manager.disconnect(websocket, user_id)
            
    except (JWTError, Exception) as e:
        await websocket.close(code=1008, reason=f"Authentication failed: {str(e)}")

# Mount static files directory for the web interface
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Serve the HTML interface
@app.get("/web", include_in_schema=False)
async def serve_html_interface():
    """
    Serve the HTML interface for the web application.
    This route serves the index.html file from the static folder.
    """
    return FileResponse("app/static/index.html")

# Custom OpenAPI and Swagger UI with security scheme
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        title=f"{settings.PROJECT_NAME} - Swagger UI",
        oauth2_redirect_url=None,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get(f"{settings.API_V1_STR}/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="API documentation with security scheme",
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"] = {
        "securitySchemes": {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    }
    
    # Add security requirement to all operations
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            # Skip the token endpoint (login)
            if path == f"{settings.API_V1_STR}/token" and method == "post":
                continue
                
            openapi_schema["paths"][path][method]["security"] = [{"Bearer": []}]
    
    return openapi_schema

@app.get("/")
def root():
    """
    Root endpoint that redirects to the web interface
    """
    return {
        "message": "Welcome to FastAPI Backend",
        "web_interface_url": "/web",
        "docs_url": "/docs",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json"
    }