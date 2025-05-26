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
async def person_swap(request: Request, files: List[UploadFile] = File(...)):
    user = await get_current_user_optional(request)
    
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Minimum 2 images required for person swap")
    
    try:
        # Save uploaded files
        file_id = str(uuid.uuid4())
        upload_paths = []
        
        for i, file in enumerate(files):
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"File {i+1} must be an image")
            
            upload_path = f"uploads/{file_id}_{i}_{file.filename}"
            with open(upload_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            upload_paths.append(upload_path)
        
        # Process person swap
        output_paths = await image_processor.person_swap(upload_paths, file_id)
        
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
        for upload_path in upload_paths:
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
async def add_frame(request: Request, frame_style: str = Form(...), file: UploadFile = File(...)):
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
        output_path = await image_processor.add_frame(upload_path, frame_style, file_id)
        
        # Save to database if user is authenticated
        if user:
            db = get_db()
            processed_image = ProcessedImage(
                user_id=user.id,
                original_filename=file.filename,
                processed_filename=os.path.basename(output_path),
                processing_type=f"frame_{frame_style}"
            )
            db.add(processed_image)
            db.commit()
        
        # Clean up upload
        os.remove(upload_path)
        
        return {"success": True, "output_path": f"/processed/{os.path.basename(output_path)}"}
    
    except Exception as e:
        logger.error(f"Error adding frame: {e}")
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
