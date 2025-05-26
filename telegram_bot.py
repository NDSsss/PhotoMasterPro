import os
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import aiofiles
import uuid

from image_processor import ImageProcessor
from models import User, ProcessedImage, get_db

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "your-bot-token-here")
        self.image_processor = ImageProcessor()
        self.user_states = {}  # Store user states for multi-step operations
        
    async def start(self):
        """Start the Telegram bot"""
        if self.token == "your-bot-token-here":
            logger.warning("Telegram bot token not configured, skipping bot startup")
            return
            
        try:
            application = Application.builder().token(self.token).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(CallbackQueryHandler(self.button_callback))
            application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
            
            # Start the bot
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
            
            # Keep running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        welcome_text = f"""
🎨 Добро пожаловать в PhotoProcessor Bot!

Привет, {user.first_name}! Я помогу вам обработать ваши фотографии.

Доступные функции:
• 🖼️ Удаление фона
• 📷 Создание коллажей (полароид, 5x15, 5x5)
• 🖼️ Добавление рамок
• ✨ Автоматическая ретушь

Выберите действие из меню ниже или отправьте фото для быстрой обработки.
        """
        
        keyboard = [
            [KeyboardButton("🖼️ Удалить фон"), KeyboardButton("📷 Создать коллаж")],
            [KeyboardButton("🖼️ Добавить рамку"), KeyboardButton("✨ Ретушь фото")],
            [KeyboardButton("ℹ️ Помощь")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📖 Руководство по использованию PhotoProcessor Bot

🖼️ **Удаление фона**
Отправьте фото, и я уберу фон, оставив только главный объект.

📷 **Создание коллажей**
• Полароид - 1 фото с подписью и логотипом
• 5x15 - 3 фото в горизонтальной полосе
• 5x5 - 2 фото в квадратном формате

🖼️ **Добавление рамок**
Выберите стиль рамки: классическая, современная, винтаж или элегантная.

✨ **Автоматическая ретушь**
Улучшение яркости, контраста, резкости и цветопередачи.

💡 **Быстрый способ**: просто отправьте фото, и я предложу варианты обработки!
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        text = update.message.text
        user_id = update.effective_user.id
        
        if text == "🖼️ Удалить фон":
            await self.request_photo_for_background_removal(update, context)
        elif text == "📷 Создать коллаж":
            await self.show_collage_options(update, context)
        elif text == "🖼️ Добавить рамку":
            await self.request_photo_for_frame(update, context)
        elif text == "✨ Ретушь фото":
            await self.request_photo_for_retouch(update, context)
        elif text == "ℹ️ Помощь":
            await self.help_command(update, context)
        else:
            # Handle captions for collages
            if user_id in self.user_states and self.user_states[user_id].get("waiting_for_caption"):
                self.user_states[user_id]["caption"] = text
                self.user_states[user_id]["waiting_for_caption"] = False
                await update.message.reply_text("Отлично! Теперь отправьте фотографии для коллажа.")
            else:
                await update.message.reply_text("Выберите действие из меню или отправьте фото для обработки.")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages"""
        user_id = update.effective_user.id
        
        # Check if user is in a specific workflow
        if user_id in self.user_states:
            state = self.user_states[user_id]
            
            if state.get("action") == "remove_background":
                await self.process_background_removal(update, context)
            elif state.get("action") == "add_frame":
                await self.show_frame_options(update, context)
            elif state.get("action") == "retouch":
                await self.process_retouch(update, context)
            elif state.get("action") == "collage":
                await self.collect_collage_photos(update, context)
            else:
                await self.show_photo_options(update, context)
        else:
            # Show options for the photo
            await self.show_photo_options(update, context)
    
    async def show_photo_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show processing options for uploaded photo"""
        keyboard = [
            [InlineKeyboardButton("🖼️ Удалить фон", callback_data="quick_remove_bg")],
            [InlineKeyboardButton("🖼️ Добавить рамку", callback_data="quick_add_frame")],
            [InlineKeyboardButton("✨ Ретушь", callback_data="quick_retouch")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Что сделать с этим фото?",
            reply_markup=reply_markup
        )
        
        # Store photo for processing
        user_id = update.effective_user.id
        photo = update.message.photo[-1]  # Get highest resolution
        self.user_states[user_id] = {"current_photo": photo}
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "quick_remove_bg":
            await self.process_quick_background_removal(query, context)
        elif data == "quick_add_frame":
            await self.show_frame_options_for_current_photo(query, context)
        elif data == "quick_retouch":
            await self.process_quick_retouch(query, context)
        elif data.startswith("frame_"):
            frame_style = data.replace("frame_", "")
            await self.process_frame_addition(query, context, frame_style)
        elif data.startswith("collage_"):
            collage_type = data.replace("collage_", "")
            await self.start_collage_process(query, context, collage_type)
    
    async def request_photo_for_background_removal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request photo for background removal"""
        user_id = update.effective_user.id
        self.user_states[user_id] = {"action": "remove_background"}
        
        await update.message.reply_text("Отправьте фото для удаления фона.")
    
    async def process_background_removal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process background removal"""
        try:
            await update.message.reply_text("🔄 Удаляю фон... Это может занять несколько секунд.")
            
            # Download photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            file_id = str(uuid.uuid4())
            input_path = f"uploads/{file_id}_input.jpg"
            
            await file.download_to_drive(input_path)
            
            # Process
            output_path = await self.image_processor.remove_background(input_path, file_id)
            
            # Send result
            with open(output_path, 'rb') as f:
                await update.message.reply_photo(
                    photo=f,
                    caption="✅ Фон успешно удален!"
                )
            
            # Cleanup
            os.remove(input_path)
            
            # Clear state
            user_id = update.effective_user.id
            if user_id in self.user_states:
                del self.user_states[user_id]
                
        except Exception as e:
            logger.error(f"Error in background removal: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке фото.")
    
    async def process_quick_background_removal(self, query, context):
        """Process quick background removal from inline button"""
        try:
            await query.edit_message_text("🔄 Удаляю фон... Это может занять несколько секунд.")
            
            user_id = query.from_user.id
            if user_id not in self.user_states or "current_photo" not in self.user_states[user_id]:
                await query.edit_message_text("❌ Фото не найдено. Попробуйте еще раз.")
                return
            
            photo = self.user_states[user_id]["current_photo"]
            file = await context.bot.get_file(photo.file_id)
            
            file_id = str(uuid.uuid4())
            input_path = f"uploads/{file_id}_input.jpg"
            
            await file.download_to_drive(input_path)
            
            # Process
            output_path = await self.image_processor.remove_background(input_path, file_id)
            
            # Send result
            with open(output_path, 'rb') as f:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=f,
                    caption="✅ Фон успешно удален!"
                )
            
            await query.edit_message_text("✅ Обработка завершена!")
            
            # Cleanup
            os.remove(input_path)
            del self.user_states[user_id]
                
        except Exception as e:
            logger.error(f"Error in quick background removal: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке фото.")
    
    async def show_collage_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show collage type options"""
        keyboard = [
            [InlineKeyboardButton("📷 Полароид (1 фото)", callback_data="collage_polaroid")],
            [InlineKeyboardButton("📷 5x15 (3 фото)", callback_data="collage_5x15")],
            [InlineKeyboardButton("📷 5x5 (2 фото)", callback_data="collage_5x5")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите тип коллажа:",
            reply_markup=reply_markup
        )
    
    async def start_collage_process(self, query, context, collage_type):
        """Start collage creation process"""
        user_id = query.from_user.id
        
        # Required photos for each type
        required_photos = {"polaroid": 1, "5x15": 3, "5x5": 2}
        count = required_photos[collage_type]
        
        self.user_states[user_id] = {
            "action": "collage",
            "collage_type": collage_type,
            "required_photos": count,
            "photos": [],
            "caption": ""
        }
        
        if collage_type == "polaroid":
            await query.edit_message_text("Напишите подпись для полароида (или отправьте пустое сообщение):")
            self.user_states[user_id]["waiting_for_caption"] = True
        else:
            await query.edit_message_text(f"Отправьте {count} фотографии для коллажа {collage_type}.")
    
    async def collect_collage_photos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect photos for collage"""
        user_id = update.effective_user.id
        state = self.user_states[user_id]
        
        # Add photo to collection
        photo = update.message.photo[-1]
        state["photos"].append(photo)
        
        collected = len(state["photos"])
        required = state["required_photos"]
        
        if collected < required:
            await update.message.reply_text(f"Получено {collected}/{required} фото. Отправьте еще {required - collected}.")
        else:
            # Process collage
            await self.process_collage(update, context)
    
    async def process_collage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process collage creation"""
        try:
            await update.message.reply_text("🔄 Создаю коллаж... Подождите немного.")
            
            user_id = update.effective_user.id
            state = self.user_states[user_id]
            
            # Download photos
            file_id = str(uuid.uuid4())
            input_paths = []
            
            for i, photo in enumerate(state["photos"]):
                file = await context.bot.get_file(photo.file_id)
                input_path = f"uploads/{file_id}_input_{i}.jpg"
                await file.download_to_drive(input_path)
                input_paths.append(input_path)
            
            # Process collage
            output_path = await self.image_processor.create_collage(
                input_paths, 
                state["collage_type"], 
                state["caption"], 
                file_id
            )
            
            # Send result
            with open(output_path, 'rb') as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=f"✅ Коллаж {state['collage_type']} готов!"
                )
            
            # Cleanup
            for path in input_paths:
                os.remove(path)
            
            del self.user_states[user_id]
                
        except Exception as e:
            logger.error(f"Error creating collage: {e}")
            await update.message.reply_text("❌ Произошла ошибка при создании коллажа.")
    
    async def request_photo_for_frame(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request photo for frame addition"""
        user_id = update.effective_user.id
        self.user_states[user_id] = {"action": "add_frame"}
        
        await update.message.reply_text("Отправьте фото для добавления рамки.")
    
    async def show_frame_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show frame style options"""
        await self.show_frame_options_for_current_photo(update, context)
    
    async def show_frame_options_for_current_photo(self, query_or_update, context):
        """Show frame options for current photo"""
        keyboard = [
            [InlineKeyboardButton("🎨 Классическая", callback_data="frame_classic")],
            [InlineKeyboardButton("🏢 Современная", callback_data="frame_modern")],
            [InlineKeyboardButton("📜 Винтаж", callback_data="frame_vintage")],
            [InlineKeyboardButton("💎 Элегантная", callback_data="frame_elegant")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "Выберите стиль рамки:"
        
        if hasattr(query_or_update, 'edit_message_text'):
            await query_or_update.edit_message_text(text, reply_markup=reply_markup)
        else:
            await query_or_update.message.reply_text(text, reply_markup=reply_markup)
    
    async def process_frame_addition(self, query, context, frame_style):
        """Process frame addition"""
        try:
            await query.edit_message_text(f"🔄 Добавляю {frame_style} рамку...")
            
            user_id = query.from_user.id
            if user_id not in self.user_states or "current_photo" not in self.user_states[user_id]:
                await query.edit_message_text("❌ Фото не найдено. Попробуйте еще раз.")
                return
            
            photo = self.user_states[user_id]["current_photo"]
            file = await context.bot.get_file(photo.file_id)
            
            file_id = str(uuid.uuid4())
            input_path = f"uploads/{file_id}_input.jpg"
            
            await file.download_to_drive(input_path)
            
            # Process
            output_path = await self.image_processor.add_frame(input_path, frame_style, file_id)
            
            # Send result
            with open(output_path, 'rb') as f:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=f,
                    caption=f"✅ {frame_style.title()} рамка добавлена!"
                )
            
            await query.edit_message_text("✅ Обработка завершена!")
            
            # Cleanup
            os.remove(input_path)
            del self.user_states[user_id]
                
        except Exception as e:
            logger.error(f"Error adding frame: {e}")
            await query.edit_message_text("❌ Произошла ошибка при добавлении рамки.")
    
    async def request_photo_for_retouch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request photo for retouching"""
        user_id = update.effective_user.id
        self.user_states[user_id] = {"action": "retouch"}
        
        await update.message.reply_text("Отправьте фото для автоматической ретуши.")
    
    async def process_retouch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process photo retouching"""
        try:
            await update.message.reply_text("🔄 Ретуширую фото... Это может занять несколько секунд.")
            
            # Download photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            file_id = str(uuid.uuid4())
            input_path = f"uploads/{file_id}_input.jpg"
            
            await file.download_to_drive(input_path)
            
            # Process
            output_path = await self.image_processor.retouch_image(input_path, file_id)
            
            # Send result
            with open(output_path, 'rb') as f:
                await update.message.reply_photo(
                    photo=f,
                    caption="✅ Фото отретушировано!"
                )
            
            # Cleanup
            os.remove(input_path)
            
            # Clear state
            user_id = update.effective_user.id
            if user_id in self.user_states:
                del self.user_states[user_id]
                
        except Exception as e:
            logger.error(f"Error in retouching: {e}")
            await update.message.reply_text("❌ Произошла ошибка при ретуши фото.")
    
    async def process_quick_retouch(self, query, context):
        """Process quick retouch from inline button"""
        try:
            await query.edit_message_text("🔄 Ретуширую фото... Это может занять несколько секунд.")
            
            user_id = query.from_user.id
            if user_id not in self.user_states or "current_photo" not in self.user_states[user_id]:
                await query.edit_message_text("❌ Фото не найдено. Попробуйте еще раз.")
                return
            
            photo = self.user_states[user_id]["current_photo"]
            file = await context.bot.get_file(photo.file_id)
            
            file_id = str(uuid.uuid4())
            input_path = f"uploads/{file_id}_input.jpg"
            
            await file.download_to_drive(input_path)
            
            # Process
            output_path = await self.image_processor.retouch_image(input_path, file_id)
            
            # Send result
            with open(output_path, 'rb') as f:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=f,
                    caption="✅ Фото отретушировано!"
                )
            
            await query.edit_message_text("✅ Обработка завершена!")
            
            # Cleanup
            os.remove(input_path)
            del self.user_states[user_id]
                
        except Exception as e:
            logger.error(f"Error in quick retouch: {e}")
            await query.edit_message_text("❌ Произошла ошибка при ретуши фото.")
