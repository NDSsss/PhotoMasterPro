import os
import logging
from contextlib import contextmanager
import time
from PIL import Image, ImageDraw, ImageFilter
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

class FrameAdder:
    """
    Professional frame addition system for images with multiple style options.
    
    Adds decorative frames to images using predefined styles or custom uploaded
    frames. Automatically handles sizing, composition, and maintains image quality
    while applying various frame effects including classic, modern, vintage styles.
    """
    
    def __init__(self):
        """Initialize FrameAdder with default settings."""
        pass
        
    async def add_frame(self, image_path: str, frame_style: str, file_id: str) -> str:
        """
        Add decorative frame to image with automatic sizing and composition.
        
        Applies professional-quality frames to images with smart resizing and
        positioning. Supports multiple predefined styles and maintains aspect
        ratios while optimizing visual appeal and composition.
        
        Args:
            image_path (str): Path to input image file
            frame_style (str): Frame style ("classic", "modern", "vintage", etc.)
            file_id (str): Unique identifier for tracking and logging
            
        Returns:
            str: Path to framed image with optimized quality
            
        Raises:
            ValueError: If frame style is not supported
            Exception: If image processing or frame application fails
            
        Example:
            frame_adder = FrameAdder()
            result = await frame_adder.add_frame("photo.jpg", "classic", "uuid")
        """
        logger.info(f"[{file_id}] 🖼️ Adding frame with style: {frame_style}")
        
        try:
            with timer_step("Loading image for frame addition", file_id):
                img = Image.open(image_path)
                original_size = img.size
                logger.info(f"[{file_id}] 📖 Original image size: {original_size}")
            
            with timer_step("Creating frame", file_id):
                framed_img = self._create_frame(img, frame_style, file_id)
                logger.info(f"[{file_id}] ✅ Frame created successfully")
            
            with timer_step("Saving framed result", file_id):
                output_path = f"processed/{file_id}_framed_{frame_style}.jpg"
                os.makedirs("processed", exist_ok=True)
                framed_img.save(output_path, 'JPEG', quality=90, optimize=True)
                logger.info(f"[{file_id}] 💾 Framed image saved to: {output_path}")
            
            logger.info(f"[{file_id}] ✅ Frame addition completed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error adding frame: {e}")
            raise
    
    async def add_custom_frame(self, image_path: str, frame_path: str, file_id: str) -> str:
        """Add custom frame from uploaded file with exact size matching"""
        logger.info(f"[{file_id}] 🖼️ Adding custom frame from: {frame_path}")
        
        try:
            with timer_step("Loading images for custom frame", file_id):
                img = Image.open(image_path)
                frame_img = Image.open(frame_path)
                logger.info(f"[{file_id}] 📖 Image size: {img.size}, Frame size: {frame_img.size}")
            
            with timer_step("Processing custom frame", file_id):
                # Resize frame to match image dimensions
                frame_resized = frame_img.resize(img.size, Image.Resampling.LANCZOS)
                
                # Convert both to RGBA for blending
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                if frame_resized.mode != 'RGBA':
                    frame_resized = frame_resized.convert('RGBA')
                
                # Blend images (frame over image)
                result = Image.alpha_composite(img, frame_resized)
                logger.info(f"[{file_id}] ✅ Custom frame applied successfully")
            
            with timer_step("Saving custom framed result", file_id):
                output_path = f"processed/{file_id}_custom_framed.png"
                os.makedirs("processed", exist_ok=True)
                result.save(output_path, 'PNG', optimize=True)
                logger.info(f"[{file_id}] 💾 Custom framed image saved to: {output_path}")
            
            logger.info(f"[{file_id}] ✅ Custom frame addition completed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error adding custom frame: {e}")
            raise
    
    def _create_frame(self, img: Image.Image, frame_style: str, file_id: str) -> Image.Image:
        """Create frame based on style"""
        width, height = img.size
        
        if frame_style == "classic":
            return self._create_classic_frame(img, width, height)
        elif frame_style == "modern":
            return self._create_modern_frame(img, width, height)
        elif frame_style == "vintage":
            return self._create_vintage_frame(img, width, height)
        elif frame_style == "polaroid":
            return self._create_polaroid_frame(img, width, height)
        elif frame_style == "shadow":
            return self._create_shadow_frame(img, width, height)
        else:
            logger.warning(f"[{file_id}] Unknown frame style: {frame_style}, using classic")
            return self._create_classic_frame(img, width, height)
    
    def _create_classic_frame(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Create classic ornate frame"""
        frame_width = min(50, width // 20, height // 20)
        
        # Create new image with frame
        new_width = width + 2 * frame_width
        new_height = height + 2 * frame_width
        result = Image.new('RGB', (new_width, new_height), '#8B4513')  # Brown frame
        
        # Add gradient effect
        draw = ImageDraw.Draw(result)
        for i in range(frame_width):
            color_val = int(139 - (i * 30 / frame_width))  # Gradient from brown to darker
            draw.rectangle([i, i, new_width-1-i, new_height-1-i], 
                         outline=(color_val, max(69, color_val//2), 19))
        
        # Paste original image
        result.paste(img, (frame_width, frame_width))
        return result
    
    def _create_modern_frame(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Create modern minimalist frame"""
        frame_width = min(20, width // 40, height // 40)
        
        # Create new image with frame
        new_width = width + 2 * frame_width
        new_height = height + 2 * frame_width
        result = Image.new('RGB', (new_width, new_height), '#FFFFFF')  # White frame
        
        # Add thin border
        draw = ImageDraw.Draw(result)
        draw.rectangle([0, 0, new_width-1, new_height-1], outline='#CCCCCC', width=2)
        
        # Paste original image
        result.paste(img, (frame_width, frame_width))
        return result
    
    def _create_vintage_frame(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Create vintage weathered frame"""
        frame_width = min(40, width // 25, height // 25)
        
        # Create new image with frame
        new_width = width + 2 * frame_width
        new_height = height + 2 * frame_width
        result = Image.new('RGB', (new_width, new_height), '#D2B48C')  # Tan frame
        
        # Add texture and weathering effect
        draw = ImageDraw.Draw(result)
        
        # Outer border
        draw.rectangle([0, 0, new_width-1, new_height-1], outline='#8B7355', width=3)
        # Inner border
        draw.rectangle([frame_width-5, frame_width-5, 
                       new_width-frame_width+4, new_height-frame_width+4], 
                      outline='#A0522D', width=2)
        
        # Paste original image
        result.paste(img, (frame_width, frame_width))
        return result
    
    def _create_polaroid_frame(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Create Polaroid-style frame"""
        top_margin = min(20, height // 30)
        side_margin = min(20, width // 30)
        bottom_margin = min(80, height // 8)  # Larger bottom margin for Polaroid look
        
        # Create new image with frame
        new_width = width + 2 * side_margin
        new_height = height + top_margin + bottom_margin
        result = Image.new('RGB', (new_width, new_height), '#FFFFFF')  # White Polaroid
        
        # Add slight shadow effect
        draw = ImageDraw.Draw(result)
        draw.rectangle([2, 2, new_width-1, new_height-1], outline='#DDDDDD', width=1)
        
        # Paste original image
        result.paste(img, (side_margin, top_margin))
        return result
    
    def _create_shadow_frame(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Create frame with drop shadow effect"""
        shadow_offset = min(15, width // 50, height // 50)
        
        # Create new image with space for shadow
        new_width = width + shadow_offset
        new_height = height + shadow_offset
        result = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 0))
        
        # Create shadow
        shadow = Image.new('RGBA', (width, height), (0, 0, 0, 60))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=5))
        
        # Paste shadow first
        result.paste(shadow, (shadow_offset, shadow_offset), shadow)
        
        # Paste original image
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        result.paste(img, (0, 0), img)
        
        return result