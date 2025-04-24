#!/usr/bin/env python
"""
Development server for the FastAPI application.
Use this script to run the app locally for development/debugging.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )