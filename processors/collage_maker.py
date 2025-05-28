import os
import logging
from contextlib import contextmanager
import time
from PIL import Image, ImageDraw, ImageFont
import math

# Configure logging
logger = logging.getLogger(__name__)

# Helper function for timing operations
@contextmanager
def timer_step(step_name: str, file_id: str = None):
    start_time = time.time()
    request_prefix = f"[{file_id}] " if file_id else ""
    logger.info(f"{request_prefix}🔧 STEP START: {step_name}")
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{request_prefix}✅ STEP DONE: {step_name} - Duration: {duration:.2f}s")

class CollageMaker:
    """Класс для создания коллажей и фотокарточек"""
    
    def __init__(self):
        self.logo_path = "static/images/logo.svg"
        
    async def create_collage(self, image_paths: list, collage_type: str, caption: str, file_id: str) -> str:
        """Create photo collage based on type"""
        logger.info(f"[{file_id}] 🎨 Creating {collage_type} collage with {len(image_paths)} images")
        
        try:
            with timer_step("Analyzing collage requirements", file_id):
                if collage_type == "polaroid" and len(image_paths) >= 1:
                    return await self._create_polaroid(image_paths[0], caption, file_id)
                elif collage_type == "5x15" and len(image_paths) >= 3:
                    return await self._create_5x15_collage(image_paths[:3], file_id)
                elif collage_type == "5x5" and len(image_paths) >= 2:
                    return await self._create_5x5_collage(image_paths[:2], file_id)
                elif collage_type == "magazine":
                    return await self._create_magazine_cover(image_paths, caption, file_id)
                elif collage_type == "passport":
                    return await self._create_passport_style(image_paths[0], file_id)
                elif collage_type == "filmstrip":
                    return await self._create_filmstrip(image_paths, file_id)
                elif collage_type == "grid":
                    return await self._create_grid_collage(image_paths, file_id)
                elif collage_type == "vintage_postcard":
                    return await self._create_vintage_postcard(image_paths[0], caption, file_id)
                else:
                    # Universal collage fallback
                    return await self._create_universal_collage(image_paths, caption, file_id)
                    
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error creating collage: {e}")
            raise

    async def _create_polaroid(self, image_path: str, caption: str, file_id: str) -> str:
        """Create polaroid-style photo"""
        logger.info(f"[{file_id}] 📸 Creating Polaroid style photo")
        
        with timer_step("Creating Polaroid frame", file_id):
            img = Image.open(image_path)
            
            # Resize image to square if needed
            size = min(img.size)
            img = img.crop(((img.width - size) // 2, (img.height - size) // 2,
                           (img.width + size) // 2, (img.height + size) // 2))
            img = img.resize((400, 400), Image.Resampling.LANCZOS)
            
            # Create Polaroid frame
            frame_width, frame_height = 500, 600
            polaroid = Image.new('RGB', (frame_width, frame_height), 'white')
            
            # Paste image with margins
            margin_x = (frame_width - 400) // 2
            margin_y = 50
            polaroid.paste(img, (margin_x, margin_y))
            
            # Add caption
            if caption:
                try:
                    draw = ImageDraw.Draw(polaroid)
                    font_size = 24
                    # Use default font
                    draw.text((frame_width // 2, frame_height - 80), caption, 
                             fill='black', anchor='mm')
                except Exception as e:
                    logger.warning(f"[{file_id}] Could not add caption: {e}")
            
            output_path = f"processed/{file_id}_polaroid.jpg"
            os.makedirs("processed", exist_ok=True)
            polaroid.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ Polaroid created successfully: {output_path}")
        return output_path

    async def _create_universal_collage(self, image_paths: list, caption: str, file_id: str, 
                                      background_color=(255, 255, 255), logo_text="PhotoProcessor",
                                      columns=None) -> str:
        """Универсальная функция для создания коллажей с автоматическим размещением"""
        logger.info(f"[{file_id}] 🔧 Creating universal collage with {len(image_paths)} images")
        
        with timer_step("Creating universal collage layout", file_id):
            if not image_paths:
                raise ValueError("No images provided for collage")
            
            # Calculate optimal grid
            num_images = len(image_paths)
            if columns is None:
                columns = int(math.ceil(math.sqrt(num_images)))
            rows = int(math.ceil(num_images / columns))
            
            # Load and resize images
            images = []
            target_size = (300, 300)
            
            for path in image_paths:
                img = Image.open(path)
                # Crop to square and resize
                size = min(img.size)
                img = img.crop(((img.width - size) // 2, (img.height - size) // 2,
                               (img.width + size) // 2, (img.height + size) // 2))
                img = img.resize(target_size, Image.Resampling.LANCZOS)
                images.append(img)
            
            # Calculate canvas size
            margin = 20
            canvas_width = columns * target_size[0] + (columns + 1) * margin
            canvas_height = rows * target_size[1] + (rows + 1) * margin + 100  # Extra space for text
            
            # Create canvas
            canvas = Image.new('RGB', (canvas_width, canvas_height), background_color)
            
            # Place images
            for i, img in enumerate(images):
                row = i // columns
                col = i % columns
                x = margin + col * (target_size[0] + margin)
                y = margin + row * (target_size[1] + margin)
                canvas.paste(img, (x, y))
            
            # Add caption and logo
            if caption or logo_text:
                try:
                    draw = ImageDraw.Draw(canvas)
                    
                    if caption:
                        draw.text((canvas_width // 2, canvas_height - 60), caption,
                                 fill='black', anchor='mm')
                    
                    if logo_text:
                        draw.text((canvas_width // 2, canvas_height - 20), logo_text,
                                 fill='gray', anchor='mm')
                except Exception as e:
                    logger.warning(f"[{file_id}] Could not add text: {e}")
            
            output_path = f"processed/{file_id}_universal_collage.jpg"
            os.makedirs("processed", exist_ok=True)
            canvas.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ Universal collage created: {output_path}")
        return output_path

    async def _create_5x15_collage(self, image_paths: list, file_id: str) -> str:
        """Create 5x15 collage with 3 images"""
        logger.info(f"[{file_id}] 📐 Creating 5x15 collage")
        
        with timer_step("Creating 5x15 layout", file_id):
            # 5x15 cm = roughly 2:6 ratio, using 400x1200 pixels
            canvas_width, canvas_height = 400, 1200
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            
            image_height = (canvas_height - 40) // 3  # 3 images with margins
            
            for i, path in enumerate(image_paths[:3]):
                img = Image.open(path)
                # Resize to fit width while maintaining aspect ratio
                img.thumbnail((canvas_width - 20, image_height), Image.Resampling.LANCZOS)
                
                # Center the image
                x = (canvas_width - img.width) // 2
                y = 10 + i * (image_height + 10)
                canvas.paste(img, (x, y))
            
            output_path = f"processed/{file_id}_5x15_collage.jpg"
            os.makedirs("processed", exist_ok=True)
            canvas.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ 5x15 collage created: {output_path}")
        return output_path

    async def _create_5x5_collage(self, image_paths: list, file_id: str) -> str:
        """Create 5x5 square collage with 2 images"""
        logger.info(f"[{file_id}] ⬜ Creating 5x5 square collage")
        
        with timer_step("Creating 5x5 layout", file_id):
            # 5x5 cm square, using 600x600 pixels
            canvas_size = 600
            canvas = Image.new('RGB', (canvas_size, canvas_size), 'white')
            
            # Split canvas in half
            image_height = (canvas_size - 30) // 2
            
            for i, path in enumerate(image_paths[:2]):
                img = Image.open(path)
                # Resize to fit while maintaining aspect ratio
                img.thumbnail((canvas_size - 20, image_height), Image.Resampling.LANCZOS)
                
                # Center the image
                x = (canvas_size - img.width) // 2
                y = 10 + i * (image_height + 10)
                canvas.paste(img, (x, y))
            
            output_path = f"processed/{file_id}_5x5_collage.jpg"
            os.makedirs("processed", exist_ok=True)
            canvas.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ 5x5 collage created: {output_path}")
        return output_path

    async def _create_magazine_cover(self, image_paths: list, caption: str, file_id: str) -> str:
        """Создает обложку журнала с главным фото и миниатюрами"""
        logger.info(f"[{file_id}] 📰 Creating magazine cover")
        
        with timer_step("Creating magazine layout", file_id):
            canvas_width, canvas_height = 600, 800
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            
            if image_paths:
                # Main image
                main_img = Image.open(image_paths[0])
                main_img.thumbnail((canvas_width - 40, 500), Image.Resampling.LANCZOS)
                canvas.paste(main_img, (20, 20))
                
                # Thumbnails
                if len(image_paths) > 1:
                    thumb_size = 80
                    for i, path in enumerate(image_paths[1:4]):  # Max 3 thumbnails
                        img = Image.open(path)
                        img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                        x = 20 + i * (thumb_size + 10)
                        y = canvas_height - thumb_size - 20
                        canvas.paste(img, (x, y))
            
            # Add title
            if caption:
                try:
                    draw = ImageDraw.Draw(canvas)
                    draw.text((canvas_width // 2, canvas_height - 150), caption,
                             fill='black', anchor='mm')
                except Exception:
                    pass
            
            output_path = f"processed/{file_id}_magazine_cover.jpg"
            os.makedirs("processed", exist_ok=True)
            canvas.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ Magazine cover created: {output_path}")
        return output_path

    async def _create_passport_style(self, image_path: str, file_id: str) -> str:
        """Создает фото в стиле паспорта (4 одинаковых фото)"""
        logger.info(f"[{file_id}] 🆔 Creating passport style photos")
        
        with timer_step("Creating passport layout", file_id):
            img = Image.open(image_path)
            
            # Crop to portrait format and resize
            width, height = img.size
            if width > height:
                # Crop to square first
                size = min(width, height)
                img = img.crop(((width - size) // 2, 0, (width + size) // 2, size))
            
            # Resize to passport photo size
            passport_size = (150, 200)
            img = img.resize(passport_size, Image.Resampling.LANCZOS)
            
            # Create 2x2 grid
            canvas_width = passport_size[0] * 2 + 30
            canvas_height = passport_size[1] * 2 + 30
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            
            # Place 4 copies
            positions = [(10, 10), (160, 10), (10, 210), (160, 210)]
            for pos in positions:
                canvas.paste(img, pos)
            
            output_path = f"processed/{file_id}_passport_style.jpg"
            os.makedirs("processed", exist_ok=True)
            canvas.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ Passport style photos created: {output_path}")
        return output_path

    async def _create_filmstrip(self, image_paths: list, file_id: str) -> str:
        """Создает коллаж в стиле кинопленки"""
        logger.info(f"[{file_id}] 🎬 Creating filmstrip collage")
        
        with timer_step("Creating filmstrip layout", file_id):
            frame_width, frame_height = 200, 150
            border_size = 20
            num_frames = min(len(image_paths), 6)
            
            canvas_width = frame_width + 2 * border_size
            canvas_height = (frame_height + border_size) * num_frames + border_size
            
            # Create black filmstrip background
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'black')
            
            # Add sprocket holes
            draw = ImageDraw.Draw(canvas)
            hole_size = 8
            for i in range(0, canvas_height, 20):
                # Left holes
                draw.ellipse([5, i, 5 + hole_size, i + hole_size], fill='white')
                # Right holes  
                draw.ellipse([canvas_width - 5 - hole_size, i, canvas_width - 5, i + hole_size], fill='white')
            
            # Add images
            for i, path in enumerate(image_paths[:num_frames]):
                img = Image.open(path)
                img.thumbnail((frame_width, frame_height), Image.Resampling.LANCZOS)
                
                # Center image in frame
                x = border_size + (frame_width - img.width) // 2
                y = border_size + i * (frame_height + border_size) + (frame_height - img.height) // 2
                canvas.paste(img, (x, y))
            
            output_path = f"processed/{file_id}_filmstrip.jpg"
            os.makedirs("processed", exist_ok=True)
            canvas.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ Filmstrip created: {output_path}")
        return output_path

    async def _create_grid_collage(self, image_paths: list, file_id: str) -> str:
        """Создает сетку из фотографий"""
        logger.info(f"[{file_id}] ⚏ Creating grid collage")
        return await self._create_universal_collage(image_paths, "", file_id, (240, 240, 240))

    async def _create_vintage_postcard(self, image_path: str, caption: str, file_id: str) -> str:
        """Создает винтажную открытку"""
        logger.info(f"[{file_id}] 📮 Creating vintage postcard")
        
        with timer_step("Creating vintage postcard", file_id):
            img = Image.open(image_path)
            
            # Resize image
            img.thumbnail((400, 300), Image.Resampling.LANCZOS)
            
            # Create postcard background
            canvas_width, canvas_height = 600, 400
            canvas = Image.new('RGB', (canvas_width, canvas_height), '#F5F5DC')  # Beige background
            
            # Add vintage border
            draw = ImageDraw.Draw(canvas)
            draw.rectangle([5, 5, canvas_width-6, canvas_height-6], outline='#8B4513', width=3)
            draw.rectangle([15, 15, canvas_width-16, canvas_height-16], outline='#D2691E', width=1)
            
            # Paste image
            canvas.paste(img, (20, 20))
            
            # Add postcard text area
            text_area_x = img.width + 40
            if text_area_x < canvas_width - 20:
                draw.line([text_area_x, 30, text_area_x, canvas_height-30], fill='#8B4513', width=2)
                
                # Add text lines
                for i in range(5):
                    y = 60 + i * 30
                    draw.line([text_area_x + 10, y, canvas_width - 30, y], fill='#D3D3D3', width=1)
                
                # Add caption
                if caption:
                    try:
                        draw.text((text_area_x + 20, 80), caption[:50], fill='#8B4513')
                    except Exception:
                        pass
            
            output_path = f"processed/{file_id}_vintage_postcard.jpg"
            os.makedirs("processed", exist_ok=True)
            canvas.save(output_path, 'JPEG', quality=90)
            
        logger.info(f"[{file_id}] ✅ Vintage postcard created: {output_path}")
        return output_path