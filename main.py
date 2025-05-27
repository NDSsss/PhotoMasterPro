#!/usr/bin/env python3
"""
Main entry point for deployment
"""
import uvicorn
from app import app

if __name__ == "__main__":
    # For deployment, run uvicorn server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        access_log=True
    )
else:
    # For gunicorn compatibility during deployment
    application = app