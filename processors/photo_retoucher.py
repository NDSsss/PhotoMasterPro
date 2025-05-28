import os
import logging
from contextlib import contextmanager
import time
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np

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

class PhotoRetoucher:
    """Класс для автоматической ретуши фотографий"""
    
    def __init__(self):
        pass
        
    async def retouch_image(self, image_path: str, file_id: str) -> str:
        """Perform automatic retouching"""
        logger.info(f"[{file_id}] ✨ Starting automatic photo retouching")
        
        try:
            with timer_step("Loading image for retouching", file_id):
                img = Image.open(image_path)
                original_size = img.size
                logger.info(f"[{file_id}] 📖 Original image size: {original_size}")
            
            with timer_step("Applying enhancement filters", file_id):
                enhanced_img = self._apply_enhancements(img, file_id)
                logger.info(f"[{file_id}] ✅ Enhancements applied successfully")
            
            with timer_step("Saving retouched result", file_id):
                output_path = f"processed/{file_id}_retouched.jpg"
                os.makedirs("processed", exist_ok=True)
                enhanced_img.save(output_path, 'JPEG', quality=92, optimize=True)
                logger.info(f"[{file_id}] 💾 Retouched image saved to: {output_path}")
            
            logger.info(f"[{file_id}] ✅ Photo retouching completed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error during photo retouching: {e}")
            raise
    
    def _apply_enhancements(self, img: Image.Image, file_id: str) -> Image.Image:
        """Apply various enhancement filters"""
        logger.info(f"[{file_id}] 🎨 Applying automatic enhancements")
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 1. Brightness adjustment
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.05)  # Slight brightness increase
        logger.info(f"[{file_id}] ☀️ Brightness enhanced")
        
        # 2. Contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)  # Moderate contrast boost
        logger.info(f"[{file_id}] 🌈 Contrast enhanced")
        
        # 3. Color saturation
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.08)  # Slight saturation boost
        logger.info(f"[{file_id}] 🎨 Color saturation enhanced")
        
        # 4. Sharpness enhancement
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.15)  # Moderate sharpening
        logger.info(f"[{file_id}] 🔍 Sharpness enhanced")
        
        # 5. Noise reduction (using bilateral filter via OpenCV)
        try:
            # Convert PIL to OpenCV format
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Apply bilateral filter for noise reduction while preserving edges
            filtered = cv2.bilateralFilter(img_cv, 9, 75, 75)
            
            # Convert back to PIL
            img = Image.fromarray(cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB))
            logger.info(f"[{file_id}] 🔇 Noise reduction applied")
            
        except Exception as e:
            logger.warning(f"[{file_id}] ⚠️ Could not apply noise reduction: {e}")
        
        # 6. Subtle gaussian blur for skin smoothing (very light)
        try:
            # Create a blurred version
            blurred = img.filter(ImageFilter.GaussianBlur(radius=0.8))
            
            # Blend original with blurred (20% blur, 80% original)
            img = Image.blend(img, blurred, 0.2)
            logger.info(f"[{file_id}] 🌟 Skin smoothing applied")
            
        except Exception as e:
            logger.warning(f"[{file_id}] ⚠️ Could not apply skin smoothing: {e}")
        
        logger.info(f"[{file_id}] ✅ All enhancements applied successfully")
        return img