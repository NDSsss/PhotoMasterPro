from app import app

# Для gunicorn нужен простой экспорт приложения
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
