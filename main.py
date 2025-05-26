from app import app

# Простой экспорт для прямого запуска
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
