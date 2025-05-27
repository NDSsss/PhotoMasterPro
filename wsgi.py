"""
WSGI entry point for deployment with gunicorn
"""
from app import app

# For gunicorn compatibility
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)