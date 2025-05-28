import os
import logging
import time
from contextlib import contextmanager

# Import specialized processors
from processors.background_remover import BackgroundRemover
from processors.smart_cropper import SmartCropper
from processors.frame_adder import FrameAdder
from processors.collage_maker import CollageMaker
from processors.social_optimizer import SocialOptimizer
from processors.photo_retoucher import PhotoRetoucher
from processors.person_swapper import PersonSwapper

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

def optimize_image_quality(image, max_size=(1920, 1080), quality=85):
    """Оптимизирует качество изображения без потери качества"""
    from PIL import Image
    # Проверяем размер
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    return image

class ImageProcessor:
    def __init__(self):
        self.logo_path = "static/images/logo.svg"
        
        # Initialize specialized processors
        self.background_remover = BackgroundRemover()
        self.smart_cropper = SmartCropper()
        self.frame_adder = FrameAdder()
        self.collage_maker = CollageMaker()
        self.social_optimizer = SocialOptimizer()
        self.photo_retoucher = PhotoRetoucher()
        self.person_swapper = PersonSwapper()
        
        logger.info("🎨 ImageProcessor initialized with modular architecture")
        
    # Background removal
    async def remove_background(self, input_path: str, file_id: str, method: str = "rembg") -> str:
        """Remove background from image using specified method"""
        return await self.background_remover.remove_background(input_path, file_id, method)
    
    # Smart cropping
    async def smart_crop(self, image_path: str, aspect_ratio: str, file_id: str) -> str:
        """Smart crop image to desired aspect ratio with intelligent focus"""
        return await self.smart_cropper.smart_crop(image_path, aspect_ratio, file_id)
    
    # Frame addition
    async def add_frame(self, image_path: str, frame_style: str, file_id: str) -> str:
        """Add decorative frame to image with smart cropping"""
        return await self.frame_adder.add_frame(image_path, frame_style, file_id)
    
    async def add_custom_frame(self, image_path: str, frame_path: str, file_id: str) -> str:
        """Add custom frame from uploaded file with exact size matching"""
        return await self.frame_adder.add_custom_frame(image_path, frame_path, file_id)
    
    # Collage creation
    async def create_collage(self, image_paths: list, collage_type: str, caption: str, file_id: str) -> str:
        """Create photo collage based on type"""
        return await self.collage_maker.create_collage(image_paths, collage_type, caption, file_id)
    
    # Social media optimization
    async def optimize_for_social_media(self, image_path: str, file_id: str) -> dict:
        """One-click social media optimization - creates optimized versions for all major platforms"""
        return await self.social_optimizer.optimize_for_social_media(image_path, file_id)
    
    # Photo retouching
    async def retouch_image(self, image_path: str, file_id: str) -> str:
        """Perform automatic retouching"""
        return await self.photo_retoucher.retouch_image(image_path, file_id)
    
    # Person swapping
    async def person_swap(self, image_paths: list, file_id: str) -> list:
        """Подставляет людей с первых фото на фоны с остальных фото"""
        return await self.person_swapper.person_swap(image_paths, file_id)
    
    async def person_swap_separate(self, person_paths: list, background_paths: list, file_id: str) -> list:
        """Подставляет каждого человека на каждый фон (отдельные массивы)"""
        return await self.person_swapper.person_swap_separate(person_paths, background_paths, file_id)