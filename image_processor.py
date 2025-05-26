import os
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import cv2
import numpy as np
import logging

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

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        self.logo_path = "static/images/logo.svg"
        
    async def remove_background(self, input_path: str, file_id: str) -> str:
        """Remove background from image using rembg"""
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
            
            logger.info(f"Background removed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error removing background: {e}")
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
            else:
                raise ValueError(f"Unknown collage type: {collage_type}")
                
        except Exception as e:
            logger.error(f"Error creating collage: {e}")
            raise
    
    async def _create_polaroid(self, image_path: str, caption: str, file_id: str) -> str:
        """Create polaroid-style photo"""
        # Open and resize image
        img = Image.open(image_path)
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
