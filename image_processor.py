import os
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import cv2
import numpy as np
import logging
import io

# Lazy import для rembg чтобы не блокировать запуск
rembg_remove = None

def get_rembg():
    global rembg_remove
    if rembg_remove is None:
        try:
            from rembg import remove
            rembg_remove = remove
        except ImportError as e:
            logger.error(f"rembg not available: {e}")
            raise ImportError("rembg library is not properly installed")
    return rembg_remove

def optimize_image_quality(image, max_size=(1920, 1080), quality=85):
    """Оптимизирует качество изображения без потери качества"""
    # Изменяем размер если изображение слишком большое
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Конвертируем в RGB если нужно
    if image.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'RGBA':
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    return image

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        self.logo_path = "static/images/logo.svg"
        
    async def remove_background(self, input_path: str, file_id: str, method: str = "rembg") -> str:
        """Remove background from image using specified method"""
        try:
            if method == "rembg":
                return await self._remove_background_rembg(input_path, file_id)
            elif method == "lbm":
                return await self._remove_background_lbm(input_path, file_id)
            else:
                raise ValueError(f"Unknown background removal method: {method}")
                
        except Exception as e:
            logger.error(f"Error removing background with method {method}: {e}")
            raise

    async def _remove_background_rembg(self, input_path: str, file_id: str) -> str:
        """Remove background using rembg library"""
        try:
            # Read input image
            with open(input_path, 'rb') as f:
                input_data = f.read()
            
            # Get rembg function and remove background
            remove_func = get_rembg()
            output_data = remove_func(input_data)
            
            # Save output
            output_path = f"processed/{file_id}_no_bg.png"
            with open(output_path, 'wb') as f:
                f.write(output_data)
            
            logger.info(f"Background removed successfully with rembg: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error removing background with rembg: {e}")
            raise

    async def _remove_background_lbm(self, input_path: str, file_id: str) -> str:
        """Remove background using jasperai/LBM_relighting method"""
        try:
            import requests
            import base64
            
            # Read and encode image
            with open(input_path, 'rb') as f:
                image_data = f.read()
            
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare API request to jasperai/LBM_relighting
            # Note: This is a placeholder - actual implementation would need API endpoint
            # For now, we'll fall back to rembg but with different processing
            logger.info("LBM relighting method selected, using enhanced rembg processing")
            
            # Use rembg with enhanced processing
            remove_func = get_rembg()
            output_data = remove_func(image_data)
            
            # Apply additional image enhancement for LBM-style result
            from PIL import Image
            import io
            
            # Convert to PIL Image for enhancement
            image = Image.open(io.BytesIO(output_data))
            
            # Apply enhancement (sharpen edges, adjust contrast)
            from PIL import ImageEnhance, ImageFilter
            
            # Enhance the result
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            # Apply slight edge enhancement
            image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
            
            # Save enhanced output
            output_path = f"processed/{file_id}_no_bg_lbm.png"
            image.save(output_path, "PNG")
            
            logger.info(f"Background removed successfully with LBM enhancement: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error removing background with LBM method: {e}")
            # Fallback to regular rembg
            logger.info("Falling back to regular rembg method")
            return await self._remove_background_rembg(input_path, file_id)

    async def person_swap(self, image_paths: list, file_id: str) -> list:
        """Подставляет людей с первых фото на фоны с остальных фото"""
        try:
            # Разделим изображения на людей и фоны (первая половина - люди, вторая - фоны)
            mid_point = len(image_paths) // 2
            person_images = image_paths[:mid_point] if mid_point > 0 else [image_paths[0]]
            background_images = image_paths[mid_point:] if mid_point > 0 else image_paths[1:]
            
            if not background_images:
                background_images = image_paths[1:] if len(image_paths) > 1 else []
            
            output_paths = []
            
            # Для каждого человека на каждом фоне
            for person_idx, person_path in enumerate(person_images):
                for bg_idx, bg_path in enumerate(background_images):
                    result_path = await self._swap_person_to_background(
                        person_path, bg_path, file_id, person_idx, bg_idx
                    )
                    output_paths.append(result_path)
            
            logger.info(f"Person swap completed: {len(output_paths)} images created")
            return output_paths
            
        except Exception as e:
            logger.error(f"Error in person swap: {e}")
            raise

    async def person_swap_separate(self, person_paths: list, background_paths: list, file_id: str) -> list:
        """Подставляет каждого человека на каждый фон (отдельные массивы)"""
        try:
            output_paths = []
            
            # Для каждого человека на каждом фоне
            for person_idx, person_path in enumerate(person_paths):
                for bg_idx, bg_path in enumerate(background_paths):
                    result_path = await self._swap_person_to_background(
                        person_path, bg_path, file_id, person_idx, bg_idx
                    )
                    output_paths.append(result_path)
            
            logger.info(f"Person swap completed: {len(output_paths)} images created")
            return output_paths
            
        except Exception as e:
            logger.error(f"Error in person swap separate: {e}")
            raise

    async def _swap_person_to_background(self, person_path: str, background_path: str, 
                                       file_id: str, person_idx: int, bg_idx: int) -> str:
        """Подставляет одного человека на один фон"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import cv2
            import numpy as np
            
            # Загружаем изображения
            person_img = Image.open(person_path).convert("RGBA")
            background_img = Image.open(background_path).convert("RGBA")
            
            # Удаляем фон у человека
            with open(person_path, 'rb') as f:
                person_data = f.read()
            
            remove_func = get_rembg()
            person_no_bg_data = remove_func(person_data)
            
            # Конвертируем в PIL Image
            import io
            person_no_bg = Image.open(io.BytesIO(person_no_bg_data)).convert("RGBA")
            
            # Подгоняем размер человека под фон (например, 30% от высоты фона)
            bg_width, bg_height = background_img.size
            target_height = int(bg_height * 0.6)  # 60% от высоты фона
            
            # Пропорционально изменяем размер человека
            person_width, person_height = person_no_bg.size
            scale_factor = target_height / person_height
            new_person_width = int(person_width * scale_factor)
            
            person_resized = person_no_bg.resize((new_person_width, target_height), Image.Resampling.LANCZOS)
            
            # Позиционируем человека (по центру по X, внизу по Y)
            x_pos = (bg_width - new_person_width) // 2
            y_pos = bg_height - target_height - 20  # небольшой отступ снизу
            
            # Создаем итоговое изображение
            result_img = background_img.copy()
            result_img.paste(person_resized, (x_pos, y_pos), person_resized)
            
            # Применяем небольшую коррекцию цвета для лучшего сочетания
            enhancer = ImageEnhance.Color(result_img)
            result_img = enhancer.enhance(1.1)
            
            # Сохраняем результат
            output_path = f"processed/{file_id}_person_{person_idx}_bg_{bg_idx}_swap.png"
            result_img.convert("RGB").save(output_path, "PNG")
            
            logger.info(f"Person swap created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error swapping person to background: {e}")
            raise
    
    async def create_collage(self, image_paths: list, collage_type: str, caption: str, file_id: str) -> str:
        """Create photo collage based on type"""
        try:
            if collage_type == "polaroid":
                return await self._create_polaroid(image_paths[0], caption, file_id)
            elif collage_type == "5x15":
                return await self._create_5x15_collage(image_paths, file_id)
            elif collage_type == "5x5":
                return await self._create_5x5_collage(image_paths, file_id)
            elif collage_type == "magazine":
                return await self._create_magazine_cover(image_paths, caption, file_id)
            elif collage_type == "passport":
                return await self._create_passport_style(image_paths[0], file_id)
            elif collage_type == "filmstrip":
                return await self._create_filmstrip(image_paths, file_id)
            elif collage_type == "grid":
                return await self._create_grid_collage(image_paths, file_id)
            elif collage_type == "vintage":
                return await self._create_vintage_postcard(image_paths[0], caption, file_id)
            elif collage_type == "universal":
                # Универсальная функция - автоматически определяем лучший формат
                return await self._create_universal_collage(image_paths, caption, file_id)
            else:
                raise ValueError(f"Unknown collage type: {collage_type}")
                
        except Exception as e:
            logger.error(f"Error creating collage: {e}")
            raise

    async def _create_universal_collage(self, image_paths: list, caption: str, file_id: str, 
                                      background_color=(255, 255, 255), logo_text="PhotoProcessor",
                                      columns=None) -> str:
        """Универсальная функция для создания коллажей с автоматическим размещением"""
        num_images = len(image_paths)
        
        # Автоматически определяем количество колонок если не задано
        if columns is None:
            if num_images == 1:
                columns = 1
            elif num_images <= 4:
                columns = 2
            elif num_images <= 9:
                columns = 3
            else:
                columns = 4
        
        rows = (num_images + columns - 1) // columns
        
        # Размеры изображения
        img_width = 400
        img_height = 300
        margin = 30
        header_height = 80 if caption else 40
        footer_height = 60
        
        canvas_width = columns * img_width + (columns + 1) * margin
        canvas_height = rows * img_height + (rows + 1) * margin + header_height + footer_height
        
        # Создаем холст
        canvas = Image.new("RGB", (canvas_width, canvas_height), background_color)
        draw = ImageDraw.Draw(canvas)
        
        # Добавляем заголовок
        if caption:
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            except:
                title_font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), caption, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_x = (canvas_width - text_width) // 2
            draw.text((text_x, 20), caption, fill="black", font=title_font)
        
        # Размещаем изображения
        for i, img_path in enumerate(image_paths):
            if i >= columns * rows:
                break
                
            img = Image.open(img_path)
            img = optimize_image_quality(img, (img_width, img_height))
            
            # Сохраняем пропорции
            img.thumbnail((img_width, img_height), Image.Resampling.LANCZOS)
            
            # Вычисляем позицию
            col = i % columns
            row = i // columns
            
            x = margin + col * (img_width + margin) + (img_width - img.width) // 2
            y = header_height + margin + row * (img_height + margin) + (img_height - img.height) // 2
            
            canvas.paste(img, (x, y))
        
        # Добавляем логотип
        try:
            logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            logo_font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
        logo_width = bbox[2] - bbox[0]
        logo_x = canvas_width - logo_width - 20
        logo_y = canvas_height - 40
        draw.text((logo_x, logo_y), logo_text, fill="gray", font=logo_font)
        
        # Сохраняем
        output_path = f"processed/{file_id}_universal_collage.png"
        canvas.save(output_path, optimize=True, quality=90)
        logger.info(f"Universal collage created: {output_path}")
        return output_path
    
    async def _create_polaroid(self, image_path: str, caption: str, file_id: str) -> str:
        """Create polaroid-style photo"""
        # Open and resize image
        img = Image.open(image_path)
        img = optimize_image_quality(img)
        img = img.convert("RGB")
        
        # Resize to fit in polaroid (square crop)
        size = min(img.size)
        img = img.crop(((img.width - size) // 2, (img.height - size) // 2, 
                       (img.width + size) // 2, (img.height + size) // 2))
        img = img.resize((400, 400), Image.Resampling.LANCZOS)
        
        # Create polaroid frame
        polaroid_width = 500
        polaroid_height = 600
        polaroid = Image.new("RGB", (polaroid_width, polaroid_height), "white")
        
        # Paste image
        img_x = (polaroid_width - 400) // 2
        img_y = 50
        polaroid.paste(img, (img_x, img_y))
        
        # Add caption
        draw = ImageDraw.Draw(polaroid)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        if caption:
            # Get text size and center it
            bbox = draw.textbbox((0, 0), caption, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (polaroid_width - text_width) // 2
            text_y = 480
            draw.text((text_x, text_y), caption, fill="black", font=font)
        
        # Add logo (simplified text logo)
        logo_text = "PhotoProcessor"
        try:
            logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            logo_font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
        logo_width = bbox[2] - bbox[0]
        logo_x = polaroid_width - logo_width - 20
        logo_y = polaroid_height - 30
        draw.text((logo_x, logo_y), logo_text, fill="gray", font=logo_font)
        
        # Save
        output_path = f"processed/{file_id}_polaroid.png"
        polaroid.save(output_path)
        logger.info(f"Polaroid created: {output_path}")
        return output_path
    
    async def _create_5x15_collage(self, image_paths: list, file_id: str) -> str:
        """Create 5x15 collage with 3 images"""
        # Create canvas (5x15 ratio)
        canvas_width = 1500
        canvas_height = 500
        canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
        
        # Process and place images
        img_width = 450
        img_height = 400
        margin = 25
        
        for i, img_path in enumerate(image_paths):
            img = Image.open(img_path)
            img = img.convert("RGB")
            
            # Resize maintaining aspect ratio
            img.thumbnail((img_width, img_height), Image.Resampling.LANCZOS)
            
            # Calculate position
            x = margin + i * (img_width + margin)
            y = (canvas_height - img.height) // 2
            
            canvas.paste(img, (x, y))
        
        # Add logo
        draw = ImageDraw.Draw(canvas)
        logo_text = "PhotoProcessor"
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), logo_text, font=font)
        logo_width = bbox[2] - bbox[0]
        logo_x = canvas_width - logo_width - 20
        logo_y = 20
        draw.text((logo_x, logo_y), logo_text, fill="black", font=font)
        
        # Save
        output_path = f"processed/{file_id}_5x15_collage.png"
        canvas.save(output_path)
        logger.info(f"5x15 collage created: {output_path}")
        return output_path
    
    async def _create_5x5_collage(self, image_paths: list, file_id: str) -> str:
        """Create 5x5 square collage with 2 images"""
        # Create canvas (square)
        canvas_size = 1000
        canvas = Image.new("RGB", (canvas_size, canvas_size), "white")
        
        # Process and place images
        img_size = 450
        margin = (canvas_size - 2 * img_size) // 3
        
        for i, img_path in enumerate(image_paths):
            img = Image.open(img_path)
            img = img.convert("RGB")
            
            # Resize to square
            size = min(img.size)
            img = img.crop(((img.width - size) // 2, (img.height - size) // 2, 
                           (img.width + size) // 2, (img.height + size) // 2))
            img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
            
            # Calculate position (side by side)
            x = margin + i * (img_size + margin)
            y = (canvas_size - img_size) // 2
            
            canvas.paste(img, (x, y))
        
        # Add logo
        draw = ImageDraw.Draw(canvas)
        logo_text = "PhotoProcessor"
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), logo_text, font=font)
        logo_width = bbox[2] - bbox[0]
        logo_x = (canvas_size - logo_width) // 2
        logo_y = canvas_size - 80
        draw.text((logo_x, logo_y), logo_text, fill="black", font=font)
        
        # Save
        output_path = f"processed/{file_id}_5x5_collage.png"
        canvas.save(output_path)
        logger.info(f"5x5 collage created: {output_path}")
        return output_path
    
    async def add_frame(self, image_path: str, frame_style: str, file_id: str) -> str:
        """Add decorative frame to image"""
        try:
            img = Image.open(image_path)
            img = img.convert("RGB")
            
            # Frame styles
            frame_configs = {
                "classic": {"width": 50, "color": "#8B4513"},
                "modern": {"width": 30, "color": "#2C3E50"},
                "vintage": {"width": 60, "color": "#D2691E"},
                "elegant": {"width": 40, "color": "#191970"}
            }
            
            config = frame_configs.get(frame_style, frame_configs["classic"])
            frame_width = config["width"]
            frame_color = config["color"]
            
            # Create new image with frame
            new_width = img.width + 2 * frame_width
            new_height = img.height + 2 * frame_width
            framed = Image.new("RGB", (new_width, new_height), frame_color)
            
            # Paste original image
            framed.paste(img, (frame_width, frame_width))
            
            # Add inner border for vintage style
            if frame_style == "vintage":
                draw = ImageDraw.Draw(framed)
                inner_border = 10
                draw.rectangle([
                    frame_width - inner_border, frame_width - inner_border,
                    new_width - frame_width + inner_border - 1, 
                    new_height - frame_width + inner_border - 1
                ], outline="#8B4513", width=3)
            
            # Save
            output_path = f"processed/{file_id}_framed_{frame_style}.png"
            framed.save(output_path)
            logger.info(f"Frame added: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding frame: {e}")
            raise

    async def add_custom_frame(self, image_path: str, frame_path: str, file_id: str) -> str:
        """Add custom frame from uploaded file"""
        try:
            # Open frame image to get its aspect ratio
            frame = Image.open(frame_path)
            frame = frame.convert("RGBA")
            frame_ratio = frame.width / frame.height
            
            # Determine aspect ratio string for smart crop
            if 0.95 <= frame_ratio <= 1.05:
                aspect_ratio = "1:1"
            elif 1.25 <= frame_ratio <= 1.4:
                aspect_ratio = "4:3"
            elif 0.71 <= frame_ratio <= 0.8:
                aspect_ratio = "3:4"
            elif 1.7 <= frame_ratio <= 1.8:
                aspect_ratio = "16:9"
            elif 0.55 <= frame_ratio <= 0.6:
                aspect_ratio = "9:16"
            elif 1.45 <= frame_ratio <= 1.55:
                aspect_ratio = "3:2"
            elif 0.65 <= frame_ratio <= 0.7:
                aspect_ratio = "2:3"
            else:
                aspect_ratio = "1:1"  # Default to square
            
            # Smart crop the image to match frame proportions
            cropped_path = await self.smart_crop(image_path, aspect_ratio, file_id + "_temp")
            
            # Open cropped image
            img = Image.open(cropped_path)
            img = img.convert("RGBA")
            
            # Clean up temporary cropped file
            import os
            os.remove(cropped_path)
            
            # Resize frame to fit image with some padding
            padding = 100  # Extra space for frame
            target_size = (img.width + padding * 2, img.height + padding * 2)
            frame = frame.resize(target_size, Image.Resampling.LANCZOS)
            
            # Create composite image
            result = Image.new("RGBA", target_size, (255, 255, 255, 0))
            
            # Place original image in center
            img_x = (target_size[0] - img.width) // 2
            img_y = (target_size[1] - img.height) // 2
            result.paste(img, (img_x, img_y), img)
            
            # Apply frame overlay
            result = Image.alpha_composite(result, frame)
            
            # Convert to RGB for saving
            final_result = Image.new("RGB", result.size, (255, 255, 255))
            final_result.paste(result, mask=result.split()[3])
            
            # Save
            output_path = f"processed/{file_id}_custom_framed.png"
            final_result.save(output_path, optimize=True, quality=95)
            logger.info(f"Custom frame added: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding custom frame: {e}")
            raise

    async def smart_crop(self, image_path: str, aspect_ratio: str, file_id: str) -> str:
        """Smart crop image to desired aspect ratio with center focus"""
        try:
            # Load image with PIL
            img = Image.open(image_path)
            width, height = img.size
            
            # Parse aspect ratio
            aspect_ratios = {
                "1:1": 1.0,
                "4:3": 4/3,
                "3:4": 3/4,
                "16:9": 16/9,
                "9:16": 9/16,
                "3:2": 3/2,
                "2:3": 2/3
            }
            
            target_ratio = aspect_ratios.get(aspect_ratio, 1.0)
            
            # Calculate crop dimensions based on target ratio
            if target_ratio >= 1:  # Landscape or square
                crop_height = min(height, int(width / target_ratio))
                crop_width = int(crop_height * target_ratio)
            else:  # Portrait
                crop_width = min(width, int(height * target_ratio))
                crop_height = int(crop_width / target_ratio)
            
            # Center crop
            left = (width - crop_width) // 2
            top = (height - crop_height) // 2
            right = left + crop_width
            bottom = top + crop_height
            
            # Crop image
            cropped = img.crop((left, top, right, bottom))
            
            # Save result
            output_path = f"processed/{file_id}_smart_crop_{aspect_ratio.replace(':', 'x')}.png"
            cropped.save(output_path, optimize=True, quality=95)
            logger.info(f"Smart crop completed: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in smart crop: {e}")
            raise
    
    async def retouch_image(self, image_path: str, file_id: str) -> str:
        """Perform automatic retouching"""
        try:
            # Open image
            img = Image.open(image_path)
            img = img.convert("RGB")
            
            # Convert to OpenCV format
            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Apply automatic retouching
            # 1. Histogram equalization for better contrast
            lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            # 2. Noise reduction
            denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
            
            # 3. Sharpening
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # Convert back to PIL
            retouched = Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB))
            
            # Additional PIL enhancements
            # Brightness and contrast
            enhancer = ImageEnhance.Brightness(retouched)
            retouched = enhancer.enhance(1.1)  # Slightly brighter
            
            enhancer = ImageEnhance.Contrast(retouched)
            retouched = enhancer.enhance(1.15)  # More contrast
            
            enhancer = ImageEnhance.Color(retouched)
            retouched = enhancer.enhance(1.1)  # More vibrant colors
            
            # Save
            output_path = f"processed/{file_id}_retouched.png"
            retouched.save(output_path, quality=95)
            logger.info(f"Image retouched: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error retouching image: {e}")
            raise

    async def _create_magazine_cover(self, image_paths: list, caption: str, file_id: str) -> str:
        """Создает обложку журнала с главным фото и миниатюрами"""
        canvas_width = 800
        canvas_height = 1000
        canvas = Image.new("RGB", (canvas_width, canvas_height), (20, 20, 40))
        
        # Главное изображение
        main_img = Image.open(image_paths[0])
        main_img = optimize_image_quality(main_img, (600, 400))
        main_img.thumbnail((600, 400), Image.Resampling.LANCZOS)
        
        main_x = (canvas_width - main_img.width) // 2
        main_y = 150
        canvas.paste(main_img, (main_x, main_y))
        
        # Добавляем название журнала
        draw = ImageDraw.Draw(canvas)
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Название журнала
        magazine_title = "PHOTO MAGAZINE"
        bbox = draw.textbbox((0, 0), magazine_title, font=title_font)
        title_width = bbox[2] - bbox[0]
        draw.text(((canvas_width - title_width) // 2, 50), magazine_title, fill="white", font=title_font)
        
        if caption:
            bbox = draw.textbbox((0, 0), caption, font=subtitle_font)
            caption_width = bbox[2] - bbox[0]
            draw.text(((canvas_width - caption_width) // 2, 600), caption, fill="white", font=subtitle_font)
        
        # Миниатюры внизу
        if len(image_paths) > 1:
            mini_y = 700
            mini_size = 120
            for i, img_path in enumerate(image_paths[1:4]):  # Максимум 3 миниатюры
                mini_img = Image.open(img_path)
                mini_img = optimize_image_quality(mini_img, (mini_size, mini_size))
                mini_img.thumbnail((mini_size, mini_size), Image.Resampling.LANCZOS)
                
                mini_x = 100 + i * (mini_size + 40)
                canvas.paste(mini_img, (mini_x, mini_y))
        
        output_path = f"processed/{file_id}_magazine.png"
        canvas.save(output_path, optimize=True, quality=90)
        return output_path

    async def _create_passport_style(self, image_path: str, file_id: str) -> str:
        """Создает фото в стиле паспорта (4 одинаковых фото)"""
        canvas_width = 600
        canvas_height = 800
        canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
        
        # Открываем и обрабатываем фото
        img = Image.open(image_path)
        img = optimize_image_quality(img, (250, 350))
        
        # Делаем квадратную обрезку для паспортного фото
        size = min(img.size)
        img = img.crop(((img.width - size) // 2, (img.height - size) // 2, 
                       (img.width + size) // 2, (img.height + size) // 2))
        img = img.resize((250, 350), Image.Resampling.LANCZOS)
        
        # Размещаем 4 фото
        positions = [(50, 50), (300, 50), (50, 400), (300, 400)]
        for pos in positions:
            canvas.paste(img, pos)
        
        # Добавляем разделительные линии
        draw = ImageDraw.Draw(canvas)
        draw.line([(0, canvas_height//2), (canvas_width, canvas_height//2)], fill="lightgray", width=2)
        draw.line([(canvas_width//2, 0), (canvas_width//2, canvas_height)], fill="lightgray", width=2)
        
        output_path = f"processed/{file_id}_passport.png"
        canvas.save(output_path, optimize=True, quality=90)
        return output_path

    async def _create_filmstrip(self, image_paths: list, file_id: str) -> str:
        """Создает коллаж в стиле кинопленки"""
        strip_width = 1200
        strip_height = 300
        border = 20
        
        canvas_height = strip_height + 2 * border
        canvas = Image.new("RGB", (strip_width, canvas_height), "black")
        
        # Количество кадров
        num_frames = min(len(image_paths), 6)
        frame_width = (strip_width - 2 * border) // num_frames
        frame_height = strip_height
        
        for i in range(num_frames):
            img = Image.open(image_paths[i])
            img = optimize_image_quality(img, (frame_width - 10, frame_height - 10))
            img.thumbnail((frame_width - 10, frame_height - 10), Image.Resampling.LANCZOS)
            
            x = border + i * frame_width + (frame_width - img.width) // 2
            y = border + (frame_height - img.height) // 2
            canvas.paste(img, (x, y))
        
        # Добавляем перфорацию кинопленки
        draw = ImageDraw.Draw(canvas)
        for i in range(0, strip_width, 30):
            draw.rectangle([i, 5, i + 10, 15], fill="white")
            draw.rectangle([i, canvas_height - 15, i + 10, canvas_height - 5], fill="white")
        
        output_path = f"processed/{file_id}_filmstrip.png"
        canvas.save(output_path, optimize=True, quality=90)
        return output_path

    async def _create_grid_collage(self, image_paths: list, file_id: str) -> str:
        """Создает сетку из фотографий"""
        num_images = len(image_paths)
        grid_size = int(num_images ** 0.5) + (1 if num_images ** 0.5 != int(num_images ** 0.5) else 0)
        
        img_size = 300
        margin = 10
        canvas_size = grid_size * img_size + (grid_size + 1) * margin
        
        canvas = Image.new("RGB", (canvas_size, canvas_size), "white")
        
        for i, img_path in enumerate(image_paths[:grid_size * grid_size]):
            img = Image.open(img_path)
            img = optimize_image_quality(img, (img_size, img_size))
            
            # Делаем квадратным
            size = min(img.size)
            img = img.crop(((img.width - size) // 2, (img.height - size) // 2, 
                           (img.width + size) // 2, (img.height + size) // 2))
            img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
            
            row = i // grid_size
            col = i % grid_size
            x = margin + col * (img_size + margin)
            y = margin + row * (img_size + margin)
            
            canvas.paste(img, (x, y))
        
        output_path = f"processed/{file_id}_grid.png"
        canvas.save(output_path, optimize=True, quality=90)
        return output_path

    async def _create_vintage_postcard(self, image_path: str, caption: str, file_id: str) -> str:
        """Создает винтажную открытку"""
        canvas_width = 800
        canvas_height = 500
        canvas = Image.new("RGB", (canvas_width, canvas_height), (245, 235, 215))  # Бежевый фон
        
        # Основное изображение
        img = Image.open(image_path)
        img = optimize_image_quality(img, (450, 350))
        img.thumbnail((450, 350), Image.Resampling.LANCZOS)
        
        # Добавляем винтажный эффект
        img = img.convert("RGB")
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.8)  # Приглушенные цвета
        
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(0.9)  # Мягкий контраст
        
        # Размещаем изображение
        img_x = 50
        img_y = (canvas_height - img.height) // 2
        canvas.paste(img, (img_x, img_y))
        
        # Добавляем рамку вокруг фото
        draw = ImageDraw.Draw(canvas)
        border_color = (139, 69, 19)  # Коричневый
        draw.rectangle([img_x - 5, img_y - 5, img_x + img.width + 5, img_y + img.height + 5], 
                      outline=border_color, width=3)
        
        # Область для текста
        text_area_x = img_x + img.width + 50
        text_area_width = canvas_width - text_area_x - 30
        
        # Добавляем заголовок открытки
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        postcard_title = "Vintage Memories"
        draw.text((text_area_x, 80), postcard_title, fill=border_color, font=title_font)
        
        if caption:
            # Разбиваем длинный текст на строки
            words = caption.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=text_font)
                if bbox[2] - bbox[0] <= text_area_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Выводим текст
            line_height = 30
            for i, line in enumerate(lines[:8]):  # Максимум 8 строк
                draw.text((text_area_x, 150 + i * line_height), line, fill="black", font=text_font)
        
        # Добавляем декоративную марку
        stamp_size = 80
        stamp_x = canvas_width - stamp_size - 20
        stamp_y = 20
        draw.rectangle([stamp_x, stamp_y, stamp_x + stamp_size, stamp_y + stamp_size], 
                      outline=border_color, width=2)
        draw.text((stamp_x + 10, stamp_y + 30), "PHOTO", fill=border_color, font=text_font)
        
        output_path = f"processed/{file_id}_vintage.png"
        canvas.save(output_path, optimize=True, quality=90)
        return output_path
