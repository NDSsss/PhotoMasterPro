import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.requests import Request
from pydantic import BaseModel
import jwt
from passlib.context import CryptContext
import asyncio
import threading

from image_processor import ImageProcessor
from models import User, ProcessedImage, get_db, init_db
# Telegram bot временно отключен для отладки
# from telegram_bot import TelegramBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Photo Processor API", description="Automatic photo processing service")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/processed", StaticFiles(directory="processed"), name="processed")
templates = Jinja2Templates(directory="templates")

# Initialize components
image_processor = ImageProcessor()
# telegram_bot = TelegramBot()  # Временно отключен

# Models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Database initialization
init_db()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_current_user_optional(request: Request):
    """Get current user if authenticated, otherwise return None"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        db = get_db()
        user = db.query(User).filter(User.username == username).first()
        return user
    except:
        return None

# Web routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request, user: User = Depends(get_current_user)):
    db = get_db()
    images = db.query(ProcessedImage).filter(ProcessedImage.user_id == user.id).order_by(ProcessedImage.created_at.desc()).all()
    return templates.TemplateResponse("gallery.html", {"request": request, "images": images, "user": user})

# Auth endpoints
@app.post("/api/register", response_model=Token)
async def register(user: UserCreate):
    db = get_db()
    
    # Check if user exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
async def login(user: UserLogin):
    db = get_db()
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Image processing endpoints
@app.post("/api/remove-background")
async def remove_background(request: Request, file: UploadFile = File(...), method: str = Form("rembg")):
    user = await get_current_user_optional(request)
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        upload_path = f"uploads/{file_id}_{file.filename}"
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process image with selected method
        output_path = await image_processor.remove_background(upload_path, file_id, method=method)
        
        # Save to database if user is authenticated
        if user:
            db = get_db()
            processed_image = ProcessedImage(
                user_id=user.id,
                original_filename=file.filename,
                processed_filename=os.path.basename(output_path),
                processing_type=f"remove_background_{method}"
            )
            db.add(processed_image)
            db.commit()
        
        # Clean up upload
        os.remove(upload_path)
        
        return {"success": True, "output_path": f"/processed/{os.path.basename(output_path)}"}
    
    except Exception as e:
        logger.error(f"Error removing background: {e}")
        raise HTTPException(status_code=500, detail="Error processing image")

@app.post("/api/person-swap")
async def person_swap(
    request: Request,
    person_files: List[UploadFile] = File(...),
    background_files: List[UploadFile] = File(...)
):
    user = await get_current_user_optional(request)
    
    if len(person_files) < 1 or len(background_files) < 1:
        raise HTTPException(status_code=400, detail="Need at least 1 person photo and 1 background photo")
    
    try:
        file_id = str(uuid.uuid4())
        person_paths = []
        background_paths = []
        
        # Save person files
        for i, file in enumerate(person_files):
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"Person file {i+1} must be an image")
            
            upload_path = f"uploads/{file_id}_person_{i}_{file.filename}"
            with open(upload_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            person_paths.append(upload_path)
        
        # Save background files
        for i, file in enumerate(background_files):
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"Background file {i+1} must be an image")
            
            upload_path = f"uploads/{file_id}_bg_{i}_{file.filename}"
            with open(upload_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            background_paths.append(upload_path)
        
        # Process person swap
        output_paths = await image_processor.person_swap_separate(person_paths, background_paths, file_id)
        
        # Save to database if user is authenticated
        results = []
        for i, output_path in enumerate(output_paths):
            if user:
                db = get_db()
                processed_image = ProcessedImage(
                    user_id=user.id,
                    original_filename=f"person_swap_{i+1}",
                    processed_filename=os.path.basename(output_path),
                    processing_type="person_swap"
                )
                db.add(processed_image)
                db.commit()
            
            results.append({
                "success": True,
                "output_path": f"/processed/{os.path.basename(output_path)}"
            })
        
        # Clean up uploads
        for upload_path in person_paths + background_paths:
            if os.path.exists(upload_path):
                os.remove(upload_path)
        
        return {"success": True, "results": results}
    
    except Exception as e:
        logger.error(f"Error in person swap: {e}")
        raise HTTPException(status_code=500, detail="Error processing images")

@app.post("/api/create-collage")
async def create_collage(
    request: Request,
    collage_type: str = Form(...),
    caption: str = Form(""),
    files: List[UploadFile] = File(...)
):
    user = await get_current_user_optional(request)
    
    # Validate collage type and file count
    required_files = {"polaroid": 1, "5x15": 3, "5x5": 2}
    if collage_type not in required_files:
        raise HTTPException(status_code=400, detail="Invalid collage type")
    
    if len(files) != required_files[collage_type]:
        raise HTTPException(status_code=400, detail=f"Collage type '{collage_type}' requires {required_files[collage_type]} images")
    
    try:
        # Save uploaded files
        file_id = str(uuid.uuid4())
        upload_paths = []
        
        for i, file in enumerate(files):
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="All files must be images")
            
            upload_path = f"uploads/{file_id}_{i}_{file.filename}"
            with open(upload_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            upload_paths.append(upload_path)
        
        # Process collage
        output_path = await image_processor.create_collage(upload_paths, collage_type, caption, file_id)
        
        # Save to database if user is authenticated
        if user:
            db = get_db()
            processed_image = ProcessedImage(
                user_id=user.id,
                original_filename=f"{collage_type}_collage",
                processed_filename=os.path.basename(output_path),
                processing_type=f"collage_{collage_type}"
            )
            db.add(processed_image)
            db.commit()
        
        # Clean up uploads
        for path in upload_paths:
            os.remove(path)
        
        return {"success": True, "output_path": f"/processed/{os.path.basename(output_path)}"}
    
    except Exception as e:
        logger.error(f"Error creating collage: {e}")
        raise HTTPException(status_code=500, detail="Error processing images")

@app.post("/api/add-frame")
async def add_frame(
    request: Request, 
    frame_type: str = Form(...),
    file: UploadFile = File(...),
    frame_style: str = Form(None),
    frame_file: UploadFile = File(None)
):
    user = await get_current_user_optional(request)
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded image file
        file_id = str(uuid.uuid4())
        upload_path = f"uploads/{file_id}_{file.filename}"
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process frame
        if frame_type == "custom" and frame_file:
            # Save custom frame file
            frame_path = f"uploads/{file_id}_frame_{frame_file.filename}"
            with open(frame_path, "wb") as buffer:
                frame_content = await frame_file.read()
                buffer.write(frame_content)
            
            # Process with custom frame
            output_path = await image_processor.add_custom_frame(upload_path, frame_path, file_id)
            
            # Clean up frame file
            os.remove(frame_path)
            
            processing_type = "frame_custom"
        else:
            # Process with preset frame
            if not frame_style:
                frame_style = "modern"
            output_path = await image_processor.add_frame(upload_path, frame_style, file_id)
            processing_type = f"frame_{frame_style}"
        
        # Save to database if user is authenticated
        if user:
            db = get_db()
            processed_image = ProcessedImage(
                user_id=user.id,
                original_filename=file.filename,
                processed_filename=os.path.basename(output_path),
                processing_type=processing_type
            )
            db.add(processed_image)
            db.commit()
        
        # Clean up upload
        os.remove(upload_path)
        
        return {"success": True, "output_path": f"/processed/{os.path.basename(output_path)}"}
    
    except Exception as e:
        logger.error(f"Error adding frame: {e}")
        raise HTTPException(status_code=500, detail="Error processing image")

@app.post("/api/smart-crop")
async def smart_crop(
    request: Request,
    aspect_ratio: str = Form(...),
    file: UploadFile = File(...)
):
    user = await get_current_user_optional(request)
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        upload_path = f"uploads/{file_id}_{file.filename}"
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process smart crop
        output_path = await image_processor.smart_crop(upload_path, aspect_ratio, file_id)
        
        # Save to database if user is authenticated
        if user:
            db = get_db()
            processed_image = ProcessedImage(
                user_id=user.id,
                original_filename=file.filename,
                processed_filename=os.path.basename(output_path),
                processing_type=f"smart_crop_{aspect_ratio.replace(':', 'x')}"
            )
            db.add(processed_image)
            db.commit()
        
        # Clean up upload
        os.remove(upload_path)
        
        return {"success": True, "output_path": f"/processed/{os.path.basename(output_path)}"}
    
    except Exception as e:
        logger.error(f"Error in smart crop: {e}")
        raise HTTPException(status_code=500, detail="Error processing image")

@app.post("/api/social-media-optimize")
async def optimize_for_social_media(request: Request, file: UploadFile = File(...)):
    """One-click social media optimization - creates versions for all major platforms"""
    user = await get_current_user_optional(request)
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        upload_path = f"uploads/{file_id}_{file.filename}"
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process image for all social media platforms
        result = await image_processor.optimize_for_social_media(upload_path, file_id)
        
        if result["success"]:
            # Save to database if user is authenticated
            if user:
                db = get_db()
                for platform, info in result["optimized_versions"].items():
                    processed_image = ProcessedImage(
                        user_id=user.id,
                        original_filename=file.filename,
                        processed_filename=os.path.basename(info["path"]),
                        processing_type=f"social_media_{platform}"
                    )
                    db.add(processed_image)
                db.commit()
            
            # Convert paths to web-accessible URLs
            for platform, info in result["optimized_versions"].items():
                info["path"] = f"/processed/{os.path.basename(info['path'])}"
        
        # Clean up upload
        os.remove(upload_path)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in social media optimization: {e}")
        raise HTTPException(status_code=500, detail="Error processing image")

@app.post("/api/retouch")
async def retouch_image(request: Request, file: UploadFile = File(...)):
    user = await get_current_user_optional(request)
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        upload_path = f"uploads/{file_id}_{file.filename}"
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process image
        output_path = await image_processor.retouch_image(upload_path, file_id)
        
        # Save to database if user is authenticated
        if user:
            db = get_db()
            processed_image = ProcessedImage(
                user_id=user.id,
                original_filename=file.filename,
                processed_filename=os.path.basename(output_path),
                processing_type="retouch"
            )
            db.add(processed_image)
            db.commit()
        
        # Clean up upload
        os.remove(upload_path)
        
        return {"success": True, "output_path": f"/processed/{os.path.basename(output_path)}"}
    
    except Exception as e:
        logger.error(f"Error retouching image: {e}")
        raise HTTPException(status_code=500, detail="Error processing image")

@app.get("/api/my-images")
async def get_my_images(user: User = Depends(get_current_user)):
    db = get_db()
    images = db.query(ProcessedImage).filter(ProcessedImage.user_id == user.id).order_by(ProcessedImage.created_at.desc()).all()
    return {"images": [{"id": img.id, "filename": img.processed_filename, "type": img.processing_type, "created_at": img.created_at} for img in images]}

# Telegram bot временно отключен
# def start_telegram_bot():
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(telegram_bot.start())

# telegram_thread = threading.Thread(target=start_telegram_bot, daemon=True)
# telegram_thread.start()

# Create directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("processed", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Telegram webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    try:
        import json
        import requests
        
        # Get the raw update data
        update_data = await request.json()
        logger.info(f"Received Telegram update: {update_data.get('update_id', 'unknown')}")
        
        # Get bot token
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found")
            return {"status": "error", "message": "Bot token not configured"}
        
        # Extract message data
        if "message" in update_data:
            message = update_data["message"]
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            user = message.get("from", {})
            username = user.get("username", "unknown")
            
            logger.info(f"Processing message from {username}: {text}")
            
            # Simple command handling
            response_text = ""
            
            if text == "/start":
                response_text = """🎨 Добро пожаловать в PhotoProcessor Bot!

Я помогу вам обработать ваши фотографии с помощью ИИ:

📸 **Что я умею:**
• Удалять фон с фотографий
• Создавать коллажи и фотокарточки
• Добавлять рамки
• Умная обрезка под любой формат
• Ретушь и улучшение качества
• Замена фона на фотографиях

📝 **Как пользоваться:**
Просто отправьте мне фото, и я покажу все доступные варианты обработки!

🔗 **Веб-версия:** https://photo-master-pro-dddddd1997.replit.app

Отправьте любое фото для начала работы! 📷"""
                
            elif text == "/help":
                response_text = """📋 **Помощь по PhotoProcessor Bot**

🎯 **Основные функции:**
• `/start` - Начать работу с ботом
• `/help` - Показать эту справку

📸 **Обработка фото:**
Просто отправьте фото, и выберите нужную операцию:

1️⃣ **Удаление фона** - Автоматическое удаление фона
2️⃣ **Коллажи** - Создание красивых коллажей
3️⃣ **Рамки** - Добавление декоративных рамок
4️⃣ **Умная обрезка** - Обрезка под нужный формат
5️⃣ **Ретушь** - Автоматическое улучшение качества

💡 **Совет:** Для лучшего результата используйте фото хорошего качества!

🌐 **Веб-версия доступна по ссылке:**
https://photo-master-pro-dddddd1997.replit.app"""
                
            elif message.get("photo"):
                response_text = """📸 Отличное фото! Выберите, что хотите сделать:

🎨 **Доступные операции:**
• Удалить фон
• Создать коллаж 
• Добавить рамку
• Умная обрезка
• Ретушь фото

Напишите название операции или используйте веб-версию для полного функционала:
https://photo-master-pro-dddddd1997.replit.app"""
                
            else:
                response_text = """❓ Не понимаю эту команду.

📝 Попробуйте:
• `/start` - Начать работу
• `/help` - Получить справку
• Отправить фото для обработки

🌐 Или используйте веб-версию:
https://photo-master-pro-dddddd1997.replit.app"""
            
            # Send response back to Telegram
            if response_text and chat_id:
                telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": response_text,
                    "parse_mode": "Markdown"
                }
                
                response = requests.post(telegram_url, json=payload)
                if response.status_code == 200:
                    logger.info(f"Sent response to {username}")
                else:
                    logger.error(f"Failed to send response: {response.text}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
