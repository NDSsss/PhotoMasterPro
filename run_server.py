#!/usr/bin/env python3
import uvicorn
from app import app

if __name__ == "__main__":
    # Запускаем FastAPI приложение через uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=5000, 
        log_level="info"
    )