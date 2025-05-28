import os
import logging
from contextlib import contextmanager
import time
from PIL import Image, ImageFilter
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

class SmartCropper:
    """
    Intelligent image cropping system with face detection and composition analysis.
    
    Automatically crops images to desired aspect ratios while preserving important
    content like faces and applying composition rules. Uses OpenCV for face detection
    and maintains a safety margin from image edges for better visual appeal.
    """
    
    def __init__(self):
        """Initialize SmartCropper with face detection cascade."""
        self.face_cascade = None
        
    def _load_face_cascade(self):
        """Load OpenCV face detection cascade"""
        if self.face_cascade is None:
            try:
                # Try to load face detection cascade
                cascade_path = '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml'
                if not os.path.exists(cascade_path):
                    # Fallback path
                    cascade_path = 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception as e:
                logger.warning(f"Could not load face cascade: {e}")
                self.face_cascade = None
        return self.face_cascade
        
    async def smart_crop(self, image_path: str, aspect_ratio: str, file_id: str) -> str:
        """
        Intelligently crop image to target aspect ratio preserving important content.
        
        Analyzes image for faces and applies smart cropping algorithms to maintain
        visual focus while achieving desired dimensions. Includes 15% safety margin
        from edges and optimizes composition automatically.
        
        Args:
            image_path (str): Path to input image file
            aspect_ratio (str): Target ratio like "1:1", "16:9", "4:3"
            file_id (str): Unique identifier for tracking and logging
            
        Returns:
            str: Path to intelligently cropped image
            
        Raises:
            ValueError: If aspect ratio format is invalid
            Exception: If image processing or face detection fails
            
        Example:
            cropper = SmartCropper()
            result = await cropper.smart_crop("photo.jpg", "1:1", "uuid")
        """
        logger.info(f"[{file_id}] ✂️ Starting smart crop with aspect ratio: {aspect_ratio}")
        
        try:
            with timer_step("Loading image for cropping", file_id):
                img = Image.open(image_path)
                original_size = img.size
                logger.info(f"[{file_id}] 📖 Original image size: {original_size}")
            
            with timer_step("Calculating target dimensions", file_id):
                # Parse aspect ratio
                if ":" in aspect_ratio:
                    w_ratio, h_ratio = map(float, aspect_ratio.split(":"))
                elif aspect_ratio == "square":
                    w_ratio, h_ratio = 1, 1
                elif aspect_ratio == "portrait":
                    w_ratio, h_ratio = 3, 4
                elif aspect_ratio == "landscape":
                    w_ratio, h_ratio = 4, 3
                else:
                    w_ratio, h_ratio = 1, 1
                
                # Calculate target dimensions
                original_width, original_height = img.size
                target_ratio = w_ratio / h_ratio
                current_ratio = original_width / original_height
                
                if current_ratio > target_ratio:
                    # Image is too wide, crop width
                    target_width = int(original_height * target_ratio)
                    target_height = original_height
                else:
                    # Image is too tall, crop height
                    target_width = original_width
                    target_height = int(original_width / target_ratio)
                
                logger.info(f"[{file_id}] 📏 Target dimensions: {target_width}x{target_height}")
            
            with timer_step("Finding optimal crop position", file_id):
                cropped_img = self._crop_to_exact_dimensions(img, target_width, target_height)
                logger.info(f"[{file_id}] ✅ Cropping completed")
            
            with timer_step("Saving cropped result", file_id):
                output_path = f"processed/{file_id}_cropped_{aspect_ratio.replace(':', '_')}.jpg"
                os.makedirs("processed", exist_ok=True)
                cropped_img.save(output_path, 'JPEG', quality=90, optimize=True)
                logger.info(f"[{file_id}] 💾 Cropped image saved to: {output_path}")
            
            logger.info(f"[{file_id}] ✅ Smart crop completed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error during smart crop: {e}")
            raise
    
    def _crop_to_exact_dimensions(self, img, target_width, target_height):
        """Crop image to exact dimensions using smart focal point detection"""
        original_width, original_height = img.size
        
        # Find focal point (prioritize faces)
        focal_x, focal_y = self._find_focal_point(img)
        
        # Calculate crop coordinates with safety margin
        safety_margin = 0.15  # 15% margin from edges
        min_x = int(original_width * safety_margin)
        max_x = int(original_width * (1 - safety_margin)) - target_width
        min_y = int(original_height * safety_margin)
        max_y = int(original_height * (1 - safety_margin)) - target_height
        
        # Calculate optimal crop position around focal point
        crop_x = focal_x - target_width // 2
        crop_y = focal_y - target_height // 2
        
        # Constrain to image bounds with safety margin
        crop_x = max(min_x, min(crop_x, max_x))
        crop_y = max(min_y, min(crop_y, max_y))
        
        # Final bounds check
        crop_x = max(0, min(crop_x, original_width - target_width))
        crop_y = max(0, min(crop_y, original_height - target_height))
        
        return img.crop((crop_x, crop_y, crop_x + target_width, crop_y + target_height))
    
    def _find_focal_point(self, img):
        """Find the most interesting point in the image - prioritize faces"""
        width, height = img.size
        
        try:
            # Convert PIL to OpenCV format for face detection
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Load face cascade
            face_cascade = self._load_face_cascade()
            
            if face_cascade is not None:
                # Detect faces
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) > 0:
                    # Use center of largest face as focal point
                    largest_face = max(faces, key=lambda face: face[2] * face[3])
                    x, y, w, h = largest_face
                    focal_x = x + w // 2
                    focal_y = y + h // 2
                    logger.info(f"Face detected at focal point: ({focal_x}, {focal_y})")
                    return focal_x, focal_y
            
            # Fallback: use contrast-based focal point detection
            gray_array = np.array(img.convert('L'))
            max_contrast = 0
            focal_x, focal_y = width // 2, height // 2
            
            # Sample points in a grid to find highest contrast area
            for y in range(height // 4, 3 * height // 4, height // 8):
                for x in range(width // 4, 3 * width // 4, width // 8):
                    contrast = self._calculate_local_contrast(gray_array, x, y)
                    if contrast > max_contrast:
                        max_contrast = contrast
                        focal_x, focal_y = x, y
            
            logger.info(f"Contrast-based focal point: ({focal_x}, {focal_y})")
            return focal_x, focal_y
            
        except Exception as e:
            logger.warning(f"Error in focal point detection: {e}, using center")
            return width // 2, height // 2
    
    def _calculate_local_contrast(self, gray_img, x, y):
        """Calculate local contrast around a point"""
        try:
            h, w = gray_img.shape
            size = min(20, w // 10, h // 10)
            
            x1 = max(0, x - size)
            x2 = min(w, x + size)
            y1 = max(0, y - size)
            y2 = min(h, y + size)
            
            region = gray_img[y1:y2, x1:x2]
            return region.std()
        except Exception:
            return 0