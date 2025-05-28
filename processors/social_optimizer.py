import os
import logging
from contextlib import contextmanager
import time
from PIL import Image

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

class SocialOptimizer:
    """
    Professional social media image optimization system for all major platforms.
    
    Automatically creates platform-specific optimized versions of images with correct
    dimensions, aspect ratios, file sizes, and quality settings for Instagram, Facebook,
    Twitter, LinkedIn, YouTube, and TikTok. Ensures maximum engagement and quality.
    """
    
    def __init__(self):
        """Initialize SocialOptimizer with platform specifications and quality settings."""
        self.platform_specs = {
            'instagram': {'size': (1080, 1080), 'quality': 85, 'format': 'JPEG'},
            'facebook': {'size': (1200, 630), 'quality': 85, 'format': 'JPEG'},
            'twitter': {'size': (1024, 512), 'quality': 85, 'format': 'JPEG'},
            'linkedin': {'size': (1200, 627), 'quality': 90, 'format': 'JPEG'},
            'youtube': {'size': (1280, 720), 'quality': 90, 'format': 'JPEG'},
            'tiktok': {'size': (1080, 1920), 'quality': 85, 'format': 'JPEG'}
        }
        
    async def optimize_for_social_media(self, image_path: str, file_id: str) -> dict:
        """
        Create optimized versions of image for all major social media platforms.
        
        One-click optimization that generates platform-specific versions with correct
        dimensions, aspect ratios, compression, and quality settings. Maximizes visual
        impact while ensuring fast loading and compliance with platform requirements.
        
        Args:
            image_path (str): Path to input image file
            file_id (str): Unique identifier for tracking and logging
            
        Returns:
            dict: Platform-specific optimization results with paths, sizes, and metrics
            
        Raises:
            Exception: If image processing or platform optimization fails
            
        Example:
            optimizer = SocialOptimizer()
            results = await optimizer.optimize_for_social_media("photo.jpg", "uuid")
            # Returns: {"instagram": {"path": "...", "size": (1080, 1080)}, ...}
        """
        logger.info(f"[{file_id}] 📱 Starting social media optimization")
        
        try:
            with timer_step("Loading original image", file_id):
                original_img = Image.open(image_path)
                logger.info(f"[{file_id}] 📖 Original size: {original_img.size}")
            
            results = {}
            
            with timer_step("Creating platform-specific versions", file_id):
                for platform, specs in self.platform_specs.items():
                    try:
                        optimized_img = self._optimize_for_platform(original_img, specs, file_id, platform)
                        
                        output_path = f"processed/{file_id}_{platform}_optimized.{specs['format'].lower()}"
                        os.makedirs("processed", exist_ok=True)
                        
                        optimized_img.save(output_path, specs['format'], 
                                         quality=specs['quality'], optimize=True)
                        
                        # Get file size
                        file_size = self._get_file_size(output_path)
                        
                        results[platform] = {
                            'path': output_path,
                            'size': optimized_img.size,
                            'file_size': file_size,
                            'format': specs['format']
                        }
                        
                        logger.info(f"[{file_id}] ✅ {platform.capitalize()} version created: {optimized_img.size}, {file_size}")
                        
                    except Exception as e:
                        logger.error(f"[{file_id}] ❌ Error creating {platform} version: {e}")
            
            logger.info(f"[{file_id}] ✅ Social media optimization completed for {len(results)} platforms")
            return results
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error in social media optimization: {e}")
            raise
    
    def _optimize_for_platform(self, img: Image.Image, specs: dict, file_id: str, platform: str) -> Image.Image:
        """Optimize image for specific platform"""
        target_width, target_height = specs['size']
        
        # Calculate scaling to fit within target dimensions while maintaining aspect ratio
        img_ratio = img.width / img.height
        target_ratio = target_width / target_height
        
        if img_ratio > target_ratio:
            # Image is wider than target, scale by height
            new_height = target_height
            new_width = int(target_height * img_ratio)
        else:
            # Image is taller than target, scale by width
            new_width = target_width
            new_height = int(target_width / img_ratio)
        
        # Resize image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop to exact dimensions if needed
        if new_width > target_width or new_height > target_height:
            # Center crop
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height
            
            resized_img = resized_img.crop((left, top, right, bottom))
        
        # Ensure RGB mode for JPEG
        if specs['format'] == 'JPEG' and resized_img.mode in ('RGBA', 'P'):
            # Create white background for transparency
            rgb_img = Image.new('RGB', resized_img.size, (255, 255, 255))
            if resized_img.mode == 'RGBA':
                rgb_img.paste(resized_img, mask=resized_img.split()[-1])
            else:
                rgb_img.paste(resized_img)
            resized_img = rgb_img
        
        return resized_img
    
    def _get_file_size(self, file_path: str) -> str:
        """Get human-readable file size"""
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024**2:
                return f"{size_bytes/1024:.1f} KB"
            else:
                return f"{size_bytes/(1024**2):.1f} MB"
        except Exception:
            return "Unknown"