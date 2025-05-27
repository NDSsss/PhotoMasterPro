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

# User states storage
user_states = {}

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
                response_text = "🎨 *Вот что я могу:*"
                
                # Create inline keyboard with action buttons
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🖼️ Удалить фон", "callback_data": "remove_bg"},
                            {"text": "🎨 Создать коллаж", "callback_data": "collage"}
                        ],
                        [
                            {"text": "🖼️ Добавить рамку", "callback_data": "add_frame"},
                            {"text": "✂️ Умная обрезка", "callback_data": "smart_crop"}
                        ],
                        [
                            {"text": "✨ Ретушь фото", "callback_data": "retouch"},
                            {"text": "🔄 Замена фона", "callback_data": "person_swap"}
                        ],
                        [
                            {"text": "📱 Для соцсетей", "callback_data": "social_media"}
                        ],
                        [
                            {"text": "🌐 Открыть веб-версию", "url": "https://photo-master-pro-dddddd1997.replit.app"}
                        ]
                    ]
                }
                
                # Send message with inline keyboard
                telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": response_text,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard
                }
                
                response = requests.post(telegram_url, json=payload)
                if response.status_code == 200:
                    logger.info(f"Sent start message with buttons to {username}")
                else:
                    logger.error(f"Failed to send start message: {response.text}")
                
                return {"status": "ok"}
                
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
                # Handle photo based on user state
                user_id = user.get("id")
                user_state = user_states.get(user_id, {})
                action = user_state.get("action")
                
                if action == "remove_bg":
                    await process_remove_background(bot_token, chat_id, message, username)
                    return {"status": "ok"}
                elif action == "add_frame_photo":
                    await process_add_frame_photo(bot_token, chat_id, message, username, user_state)
                    return {"status": "ok"}
                elif action == "smart_crop_photo":
                    await process_smart_crop_photo(bot_token, chat_id, message, username, user_state)
                    return {"status": "ok"}
                elif action == "upload_frame":
                    await process_custom_frame_upload(bot_token, chat_id, message, username, user_state)
                    return {"status": "ok"}
                elif action == "retouch":
                    await process_retouch(bot_token, chat_id, message, username)
                    return {"status": "ok"}
                elif action == "social_media":
                    await process_social_media(bot_token, chat_id, message, username)
                    return {"status": "ok"}
                elif action == "person_swap":
                    await process_person_swap(bot_token, chat_id, message, username, user_state)
                    return {"status": "ok"}
                elif action == "collage":
                    await process_collage(bot_token, chat_id, message, username, user_state)
                    return {"status": "ok"}
                else:
                    # No active action, show menu
                    response_text = """📸 *Фото получено!* 

Выберите действие, нажав /start или кнопку ниже:"""
                    
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "🎨 Показать меню действий", "callback_data": "show_menu"}]
                        ]
                    }
                    
                    # Send message with keyboard
                    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": response_text,
                        "parse_mode": "Markdown",
                        "reply_markup": keyboard
                    }
                    response = requests.post(telegram_url, json=payload)
                    return {"status": "ok"}
                
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
        
        # Handle callback queries (button presses)
        elif "callback_query" in update_data:
            callback_query = update_data["callback_query"]
            chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
            callback_data = callback_query.get("data", "")
            query_id = callback_query.get("id")
            user = callback_query.get("from", {})
            username = user.get("username", "unknown")
            
            logger.info(f"Processing callback from {username}: {callback_data}")
            
            # Answer the callback query first
            answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
            answer_payload = {"callback_query_id": query_id}
            requests.post(answer_url, json=answer_payload)
            
            # Handle different callback actions
            response_text = ""
            
            if callback_data == "remove_bg":
                # Set user state
                user_id = user.get("id")
                user_states[user_id] = {"action": "remove_bg"}
                
                response_text = """🖼️ *Удаление фона*

Отправьте мне фото, с которого нужно удалить фон.

Я использую современные ИИ-модели для точного выделения объектов и создания прозрачного фона.

📤 *Просто отправьте фото!*"""
                
            elif callback_data == "collage":
                user_id = user.get("id")
                user_states[user_id] = {"action": "collage", "photos": []}
                
                response_text = """🎨 *Создание коллажа*

Отправьте мне 2-5 фотографий для создания красивого коллажа.

📸 *Доступные стили:*
• Полароид с подписью
• Сетка фотографий  
• Журнальная обложка
• Винтажная открытка

📤 *Отправьте первое фото!*"""
                
            elif callback_data == "add_frame":
                user_id = user.get("id")
                user_states[user_id] = {"action": "add_frame_photo"}
                
                response_text = """🖼️ *Добавление рамки*

Сначала отправьте фото, к которому хотите добавить рамку.

📤 *Отправьте фото!*"""
                
            elif callback_data == "smart_crop":
                user_id = user.get("id")
                user_states[user_id] = {"action": "smart_crop_photo"}
                
                response_text = """✂️ *Умная обрезка*

Сначала отправьте фото для обрезки.

📤 *Отправьте фото!*"""
                
            elif callback_data == "retouch":
                user_id = user.get("id")
                user_states[user_id] = {"action": "retouch"}
                
                response_text = """✨ *Ретушь фото*

Отправьте фото для автоматического улучшения качества.

🔧 *Что будет улучшено:*
• Яркость и контрастность
• Четкость изображения
• Цветовой баланс
• Устранение шумов

📤 *Отправьте фото!*"""
                
            elif callback_data == "person_swap":
                user_id = user.get("id")
                user_states[user_id] = {"action": "person_swap", "person_photos": [], "bg_photos": [], "step": "person"}
                
                response_text = """🔄 *Замена фона*

Отправьте фото человека, а затем фото с новым фоном.

🎯 *Шаг 1:* Отправьте фото с человеком

📤 *Отправьте фото человека!*"""
                
            elif callback_data == "social_media":
                user_id = user.get("id")
                user_states[user_id] = {"action": "social_media"}
                
                response_text = """📱 *Оптимизация для соцсетей*

Отправьте фото, и я создам версии для всех популярных платформ:

📱 *Создам форматы для:*
• Instagram (пост и сторис)
• Facebook (пост и обложка)
• Twitter (пост и заголовок)
• LinkedIn, YouTube, Pinterest, TikTok

📤 *Отправьте фото!*"""
                
            elif callback_data == "show_menu":
                response_text = "🎨 *Вот что я могу:*"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🖼️ Удалить фон", "callback_data": "remove_bg"},
                            {"text": "🎨 Создать коллаж", "callback_data": "collage"}
                        ],
                        [
                            {"text": "🖼️ Добавить рамку", "callback_data": "add_frame"},
                            {"text": "✂️ Умная обрезка", "callback_data": "smart_crop"}
                        ],
                        [
                            {"text": "✨ Ретушь фото", "callback_data": "retouch"},
                            {"text": "🔄 Замена фона", "callback_data": "person_swap"}
                        ],
                        [
                            {"text": "📱 Для соцсетей", "callback_data": "social_media"}
                        ],
                        [
                            {"text": "🌐 Открыть веб-версию", "url": "https://photo-master-pro-dddddd1997.replit.app"}
                        ]
                    ]
                }
            
            # Handle frame selection callbacks
            elif callback_data.startswith("frame_"):
                user_id = user.get("id")
                user_state = user_states.get(user_id, {})
                frame_type = callback_data.replace("frame_", "")
                
                if frame_type == "custom":
                    user_state["action"] = "upload_frame"
                    response_text = "📤 *Отправьте фото рамки*\n\nЗагрузите изображение рамки, которую хотите применить."
                else:
                    # Process with selected frame
                    await process_frame_with_type(bot_token, chat_id, user_state, frame_type, username)
                    return {"status": "ok"}
            
            # Handle aspect ratio selection callbacks
            elif callback_data.startswith("aspect_"):
                user_id = user.get("id")
                user_state = user_states.get(user_id, {})
                aspect_ratio = callback_data.replace("aspect_", "")
                
                if aspect_ratio == "custom":
                    user_state["action"] = "input_aspect"
                    response_text = "✏️ *Введите соотношение сторон*\n\nНапример: 16:9, 4:3, 21:9\n\nОтправьте текстом в формате ширина:высота"
                else:
                    # Process with selected aspect ratio
                    await process_crop_with_aspect(bot_token, chat_id, user_state, aspect_ratio, username)
                    return {"status": "ok"}
            
            # Send response
            if response_text and chat_id:
                telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": response_text,
                    "parse_mode": "Markdown"
                }
                
                response = requests.post(telegram_url, json=payload)
                if response.status_code == 200:
                    logger.info(f"Sent callback response to {username}")
                else:
                    logger.error(f"Failed to send callback response: {response.text}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

# Helper functions for processing photos
async def process_remove_background(bot_token, chat_id, message, username):
    """Process background removal"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Обрабатываю фото...*\n\nУдаляю фон, подождите немного!", "Markdown")
        
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Get the highest quality photo (last in the array)
        photo = message["photo"][-1]  # Telegram sends photos in ascending quality order
        file_id = photo["file_id"]
        
        # Download photo from Telegram
        photo_url = await download_telegram_photo(bot_token, file_id)
        if not photo_url:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка получения фото из Telegram.")
            return
            
        # Download and save photo to file
        import uuid
        import aiofiles
        import requests
        
        unique_id = str(uuid.uuid4())
        input_path = f"uploads/{unique_id}_input.jpg"
        
        # Download photo data
        photo_response = requests.get(photo_url)
        if photo_response.status_code != 200:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото.")
            return
            
        # Save photo to file
        async with aiofiles.open(input_path, 'wb') as f:
            await f.write(photo_response.content)
        
        # Process with ImageProcessor
        from image_processor import ImageProcessor
        processor = ImageProcessor()
        result_path = await processor.remove_background(input_path, unique_id, "rembg")
        
        # Send processed photo back to chat
        await send_telegram_photo(bot_token, chat_id, result_path, "✅ *Фон удален!*")
        
        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error in process_remove_background: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await send_telegram_message(bot_token, chat_id, f"❌ Произошла ошибка при обработке фото: {str(e)}")

async def process_add_frame_photo(bot_token, chat_id, message, username, user_state):
    """Process frame addition - first get photo, then show frame options"""
    try:
        # Save photo and show frame options
        file_id = message["photo"][-1]["file_id"]
        user_state["photo_file_id"] = file_id
        user_state["action"] = "select_frame"
        
        # Show frame selection with proper keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🖼️ Классическая", "callback_data": "frame_classic"},
                    {"text": "🎨 Современная", "callback_data": "frame_modern"}
                ],
                [
                    {"text": "📜 Винтажная", "callback_data": "frame_vintage"},
                    {"text": "📤 Загрузить свою", "callback_data": "frame_custom"}
                ]
            ]
        }
        
        # Send message with inline keyboard using requests
        import requests
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "🖼️ *Фото получено!*\n\nВыберите тип рамки:",
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
        requests.post(telegram_url, json=payload)
            
    except Exception as e:
        logger.error(f"Error in process_add_frame_photo: {e}")
        await send_telegram_message(bot_token, chat_id, "❌ Произошла ошибка при обработке фото.")

async def process_smart_crop_photo(bot_token, chat_id, message, username, user_state):
    """Process smart crop - first get photo, then show aspect ratio options"""
    try:
        # Save photo and show aspect ratio options
        file_id = message["photo"][-1]["file_id"]
        user_state["photo_file_id"] = file_id
        user_state["action"] = "select_aspect"
        
        # Show aspect ratio selection
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📱 1:1 (Квадрат)", "callback_data": "aspect_1x1"},
                    {"text": "📺 16:9 (Широкий)", "callback_data": "aspect_16x9"}
                ],
                [
                    {"text": "📷 3:4 (Портрет)", "callback_data": "aspect_3x4"},
                    {"text": "🖥️ 3:2 (Классика)", "callback_data": "aspect_3x2"}
                ],
                [
                    {"text": "✏️ Свое соотношение", "callback_data": "aspect_custom"}
                ]
            ]
        }
        
        await send_telegram_message_with_keyboard(bot_token, chat_id, 
            "✂️ *Фото получено!*\n\nВыберите соотношение сторон:", "Markdown", keyboard)
            
    except Exception as e:
        logger.error(f"Error in process_smart_crop_photo: {e}")
        await send_telegram_message(bot_token, chat_id, "❌ Произошла ошибка при обработке фото.")

async def process_add_frame(bot_token, chat_id, message, username):
    """Process frame addition"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Обрабатываю фото...*\n\nДобавляю рамку, подождите!", "Markdown")
        
        photo_url = await download_telegram_photo(bot_token, message["photo"][-1]["file_id"])
        if photo_url:
            await send_telegram_message(bot_token, chat_id, 
                "✅ *Готово!*\n\nДля полной обработки фото воспользуйтесь веб-версией:\nhttps://photo-master-pro-dddddd1997.replit.app", 
                "Markdown")
        else:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото. Попробуйте еще раз.")
            
    except Exception as e:
        logger.error(f"Error in process_add_frame: {e}")
        await send_telegram_message(bot_token, chat_id, "❌ Произошла ошибка при обработке фото.")

async def process_smart_crop(bot_token, chat_id, message, username):
    """Process smart crop"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Обрабатываю фото...*\n\nВыполняю умную обрезку!", "Markdown")
        
        photo_url = await download_telegram_photo(bot_token, message["photo"][-1]["file_id"])
        if photo_url:
            await send_telegram_message(bot_token, chat_id, 
                "✅ *Готово!*\n\nДля полной обработки фото воспользуйтесь веб-версией:\nhttps://photo-master-pro-dddddd1997.replit.app", 
                "Markdown")
        else:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото. Попробуйте еще раз.")
            
    except Exception as e:
        logger.error(f"Error in process_smart_crop: {e}")
        await send_telegram_message(bot_token, chat_id, "❌ Произошла ошибка при обработке фото.")

async def process_retouch(bot_token, chat_id, message, username):
    """Process photo retouching"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Обрабатываю фото...*\n\nВыполняю ретушь!", "Markdown")
        
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Get the highest quality photo
        photo = message["photo"][-1]
        file_id = photo["file_id"]
        
        # Download photo from Telegram
        photo_url = await download_telegram_photo(bot_token, file_id)
        if not photo_url:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка получения фото из Telegram.")
            return
            
        # Download and save photo to file
        import uuid
        import aiofiles
        import requests
        
        unique_id = str(uuid.uuid4())
        input_path = f"uploads/{unique_id}_input.jpg"
        
        # Download photo data
        photo_response = requests.get(photo_url)
        if photo_response.status_code != 200:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото.")
            return
            
        # Save photo to file
        async with aiofiles.open(input_path, 'wb') as f:
            await f.write(photo_response.content)
        
        # Process with ImageProcessor
        from image_processor import ImageProcessor
        processor = ImageProcessor()
        result_path = await processor.retouch_image(input_path, unique_id)
        
        # Send processed photo back to chat
        await send_telegram_photo(bot_token, chat_id, result_path, "✅ *Ретушь выполнена!*\n\nФото улучшено и готово к использованию.")
        
        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error in process_retouch: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await send_telegram_message(bot_token, chat_id, f"❌ Произошла ошибка при ретуши: {str(e)}")

async def process_social_media(bot_token, chat_id, message, username):
    """Process social media optimization"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Обрабатываю фото...*\n\nСоздаю версии для соцсетей!", "Markdown")
        
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Get the highest quality photo
        photo = message["photo"][-1]
        file_id = photo["file_id"]
        
        # Download photo from Telegram
        photo_url = await download_telegram_photo(bot_token, file_id)
        if not photo_url:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка получения фото из Telegram.")
            return
            
        # Download and save photo to file
        import uuid
        import aiofiles
        import requests
        
        unique_id = str(uuid.uuid4())
        input_path = f"uploads/{unique_id}_input.jpg"
        
        # Download photo data
        photo_response = requests.get(photo_url)
        if photo_response.status_code != 200:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото.")
            return
            
        # Save photo to file
        async with aiofiles.open(input_path, 'wb') as f:
            await f.write(photo_response.content)
        
        # Process with ImageProcessor
        from image_processor import ImageProcessor
        processor = ImageProcessor()
        result_data = await processor.optimize_for_social_media(input_path, unique_id)
        
        # Send summary message about created versions
        await send_telegram_message(bot_token, chat_id, 
            f"✅ *Оптимизация завершена!*\n\nСоздано {len(result_data.get('versions', []))} версий для разных платформ.\n\n🔗 Скачайте все версии на сайте:\nhttps://photo-master-pro-dddddd1997.replit.app", 
            "Markdown")
        
        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error in process_social_media: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await send_telegram_message(bot_token, chat_id, f"❌ Произошла ошибка при оптимизации: {str(e)}")

async def process_person_swap(bot_token, chat_id, message, username, user_state):
    """Process person swap"""
    try:
        step = user_state.get("step", "person")
        
        if step == "person":
            await send_telegram_message(bot_token, chat_id, "✅ *Фото человека получено!*\n\nТеперь отправьте фото с желаемым фоном.", "Markdown")
            user_state["step"] = "background"
        else:
            await send_telegram_message(bot_token, chat_id, "🔄 *Обрабатываю фото...*\n\nВыполняю замену фона!", "Markdown")
            await send_telegram_message(bot_token, chat_id, 
                "✅ *Готово!*\n\nДля полной обработки фото воспользуйтесь веб-версией:\nhttps://photo-master-pro-dddddd1997.replit.app", 
                "Markdown")
            
    except Exception as e:
        logger.error(f"Error in process_person_swap: {e}")
        await send_telegram_message(bot_token, chat_id, "❌ Произошла ошибка при обработке фото.")

async def process_collage(bot_token, chat_id, message, username, user_state):
    """Process collage creation"""
    try:
        photos = user_state.get("photos", [])
        photos.append(message["photo"][-1]["file_id"])
        user_state["photos"] = photos
        
        if len(photos) == 1:
            await send_telegram_message(bot_token, chat_id, f"✅ *Фото {len(photos)} получено!*\n\nОтправьте еще фото или нажмите /done для создания коллажа.", "Markdown")
        elif len(photos) < 5:
            await send_telegram_message(bot_token, chat_id, f"✅ *Фото {len(photos)} получено!*\n\nОтправьте еще фото или нажмите /done для создания коллажа.", "Markdown")
        else:
            await send_telegram_message(bot_token, chat_id, "🔄 *Создаю коллаж...*\n\nПодождите немного!", "Markdown")
            await send_telegram_message(bot_token, chat_id, 
                "✅ *Коллаж готов!*\n\nДля полной обработки фото воспользуйтесь веб-версией:\nhttps://photo-master-pro-dddddd1997.replit.app", 
                "Markdown")
            
    except Exception as e:
        logger.error(f"Error in process_collage: {e}")
        await send_telegram_message(bot_token, chat_id, "❌ Произошла ошибка при обработке фото.")

async def send_telegram_message(bot_token, chat_id, text, parse_mode=None):
    """Send message to Telegram"""
    import requests
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
        
    requests.post(url, json=payload)

async def download_telegram_photo(bot_token, file_id):
    """Download photo from Telegram"""
    import requests
    
    try:
        # Get file path
        file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        response = requests.get(file_url)
        
        if response.status_code == 200:
            file_path = response.json()["result"]["file_path"]
            photo_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            return photo_url
        
        return None
    except Exception as e:
        logger.error(f"Error downloading photo: {e}")
        return None

async def send_telegram_photo(bot_token, chat_id, photo_path, caption=""):
    """Send photo to Telegram chat"""
    import requests
    import os
    
    try:
        # Check if file exists
        if not os.path.exists(photo_path):
            logger.error(f"Photo file not found: {photo_path}")
            await send_telegram_message(bot_token, chat_id, f"❌ Ошибка: обработанный файл не найден")
            return False
            
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Photo sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send photo: {response.status_code} - {response.text}")
                await send_telegram_message(bot_token, chat_id, f"❌ Ошибка отправки результата. Попробуйте еще раз.")
                return False
                
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await send_telegram_message(bot_token, chat_id, f"❌ Ошибка при отправке результата: {str(e)}")
        return False

async def send_telegram_message_with_keyboard(bot_token, chat_id, text, parse_mode=None, keyboard=None):
    """Send message with inline keyboard to Telegram"""
    import requests
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if keyboard:
        payload["reply_markup"] = keyboard
        
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        logger.info(f"Message with keyboard sent to chat {chat_id}")
    else:
        logger.error(f"Failed to send message: {response.text}")

async def process_frame_with_type(bot_token, chat_id, user_state, frame_type, username):
    """Process frame addition with selected type"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Добавляю рамку...*\n\nПодождите немного!", "Markdown")
        
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Get photo from user state
        photo_file_id = user_state.get("photo_file_id")
        if not photo_file_id:
            await send_telegram_message(bot_token, chat_id, "❌ Фото не найдено. Попробуйте еще раз.")
            return
            
        # Download photo from Telegram
        photo_url = await download_telegram_photo(bot_token, photo_file_id)
        if not photo_url:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка получения фото из Telegram.")
            return
            
        # Download and save photo to file
        import uuid
        import aiofiles
        import requests
        
        unique_id = str(uuid.uuid4())
        input_path = f"uploads/{unique_id}_input.jpg"
        
        # Download photo data
        photo_response = requests.get(photo_url)
        if photo_response.status_code != 200:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото.")
            return
            
        # Save photo to file
        async with aiofiles.open(input_path, 'wb') as f:
            await f.write(photo_response.content)
        
        # Process with ImageProcessor
        from image_processor import ImageProcessor
        processor = ImageProcessor()
        result_path = await processor.add_frame(input_path, frame_type, unique_id)
        
        # Send processed photo back to chat
        frame_descriptions = {
            "classic": "классическая золотая рамка",
            "modern": "современная минималистичная рамка", 
            "vintage": "винтажная деревянная рамка"
        }
        description = frame_descriptions.get(frame_type, frame_type)
        await send_telegram_photo(bot_token, chat_id, result_path, f"✅ *Рамка добавлена!*\n\nПрименена {description}")
        
        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass
            
        # Clear user state
        user_state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_frame_with_type: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await send_telegram_message(bot_token, chat_id, f"❌ Произошла ошибка при добавлении рамки: {str(e)}")

async def process_crop_with_aspect(bot_token, chat_id, user_state, aspect_ratio, username):
    """Process smart crop with selected aspect ratio"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Выполняю умную обрезку...*\n\nПодождите немного!", "Markdown")
        
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Get photo from user state
        photo_file_id = user_state.get("photo_file_id")
        if not photo_file_id:
            await send_telegram_message(bot_token, chat_id, "❌ Фото не найдено. Попробуйте еще раз.")
            return
            
        # Download photo from Telegram
        photo_url = await download_telegram_photo(bot_token, photo_file_id)
        if not photo_url:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка получения фото из Telegram.")
            return
            
        # Download and save photo to file
        import uuid
        import aiofiles
        import requests
        
        unique_id = str(uuid.uuid4())
        input_path = f"uploads/{unique_id}_input.jpg"
        
        # Download photo data
        photo_response = requests.get(photo_url)
        if photo_response.status_code != 200:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото.")
            return
            
        # Save photo to file
        async with aiofiles.open(input_path, 'wb') as f:
            await f.write(photo_response.content)
        
        # Process with ImageProcessor
        from image_processor import ImageProcessor
        processor = ImageProcessor()
        result_path = await processor.smart_crop(input_path, aspect_ratio, unique_id)
        
        # Send processed photo back to chat
        aspect_descriptions = {
            "1x1": "квадратный формат (1:1) для Instagram",
            "16x9": "широкий формат (16:9) для YouTube и презентаций", 
            "3x4": "портретный формат (3:4) для печати",
            "3x2": "классический формат (3:2) для фотографий"
        }
        description = aspect_descriptions.get(aspect_ratio, f"формат {aspect_ratio}")
        await send_telegram_photo(bot_token, chat_id, result_path, f"✅ *Обрезка выполнена!*\n\nПрименен {description}")
        
        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass
            
        # Clear user state
        user_state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_crop_with_aspect: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await send_telegram_message(bot_token, chat_id, f"❌ Произошла ошибка при обрезке: {str(e)}")

async def process_custom_frame_upload(bot_token, chat_id, message, username, user_state):
    """Process custom frame upload"""
    try:
        await send_telegram_message(bot_token, chat_id, "🔄 *Применяю вашу рамку...*\n\nПодождите немного!", "Markdown")
        
        # Get original photo and frame from user state
        original_photo_id = user_state.get("photo_file_id")
        frame_file_id = message["photo"][-1]["file_id"]
        
        if not original_photo_id:
            await send_telegram_message(bot_token, chat_id, "❌ Исходное фото не найдено. Попробуйте еще раз.")
            return
            
        # Download both photos
        original_url = await download_telegram_photo(bot_token, original_photo_id)
        frame_url = await download_telegram_photo(bot_token, frame_file_id)
        
        if original_url and frame_url:
            from image_processor import ImageProcessor
            import uuid
            import aiofiles
            import requests
            
            # Download and save photos
            file_id = str(uuid.uuid4())
            original_path = f"uploads/{file_id}_original.jpg"
            frame_path = f"uploads/{file_id}_frame.jpg"
            
            # Download original
            response = requests.get(original_url)
            if response.status_code == 200:
                async with aiofiles.open(original_path, 'wb') as f:
                    await f.write(response.content)
            
            # Download frame
            response = requests.get(frame_url)
            if response.status_code == 200:
                async with aiofiles.open(frame_path, 'wb') as f:
                    await f.write(response.content)
            
            # Process with custom frame
            processor = ImageProcessor()
            result_path = await processor.add_custom_frame(original_path, frame_path, file_id)
            
            # Send result back
            await send_telegram_photo(bot_token, chat_id, result_path, "✅ *Ваша рамка применена!*")
        else:
            await send_telegram_message(bot_token, chat_id, "❌ Ошибка загрузки фото.")
            
        # Clear user state
        user_state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_custom_frame_upload: {e}")
        await send_telegram_message(bot_token, chat_id, "❌ Произошла ошибка при применении рамки.")
