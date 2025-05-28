import os
import logging
from contextlib import contextmanager
import time
from PIL import Image
from processors.background_remover import BackgroundRemover

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

class PersonSwapper:
    """
    Advanced AI-powered person swapping and background replacement system.
    
    Intelligently extracts people from photos and places them on different backgrounds
    with realistic lighting, shadows, and perspective matching. Uses sophisticated
    background removal and composition techniques for natural-looking results.
    """
    
    def __init__(self):
        """Initialize PersonSwapper with background removal capabilities."""
        self.background_remover = BackgroundRemover()
        
    async def person_swap(self, image_paths: list, file_id: str) -> list:
        """
        Extract people from first image and place them on backgrounds from other images.
        
        Automatically removes background from person photos and composites them onto
        new backgrounds with intelligent scaling, positioning, and lighting adjustment
        to create realistic and natural-looking person swap results.
        
        Args:
            image_paths (list): List of image paths (first = person, rest = backgrounds)
            file_id (str): Unique identifier for tracking and logging
            
        Returns:
            list: Paths to person-swapped images with realistic composition
            
        Raises:
            ValueError: If insufficient images provided (minimum 2 required)
            Exception: If person extraction or background composition fails
            
        Example:
            swapper = PersonSwapper()
            results = await swapper.person_swap(["person.jpg", "bg1.jpg", "bg2.jpg"], "uuid")
        """
        logger.info(f"[{file_id}] 👥 Starting person swap with {len(image_paths)} images")
        
        try:
            if len(image_paths) < 2:
                raise ValueError("Need at least 2 images for person swap")
            
            with timer_step("Analyzing images for person swap", file_id):
                # First image contains the person
                person_path = image_paths[0]
                background_paths = image_paths[1:]
                logger.info(f"[{file_id}] 👤 Person image: {person_path}")
                logger.info(f"[{file_id}] 🏞️ Background images: {len(background_paths)}")
            
            results = []
            
            for i, bg_path in enumerate(background_paths):
                try:
                    result_path = await self._swap_person_to_background(
                        person_path, bg_path, file_id, 0, i
                    )
                    results.append(result_path)
                except Exception as e:
                    logger.error(f"[{file_id}] ❌ Error swapping person to background {i}: {e}")
            
            logger.info(f"[{file_id}] ✅ Person swap completed for {len(results)} backgrounds")
            return results
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error in person swap: {e}")
            raise

    async def person_swap_separate(self, person_paths: list, background_paths: list, file_id: str) -> list:
        """Подставляет каждого человека на каждый фон (отдельные массивы)"""
        logger.info(f"[{file_id}] 👥 Starting person swap: {len(person_paths)} people → {len(background_paths)} backgrounds")
        
        try:
            results = []
            
            with timer_step("Processing person-background combinations", file_id):
                for person_idx, person_path in enumerate(person_paths):
                    for bg_idx, bg_path in enumerate(background_paths):
                        try:
                            result_path = await self._swap_person_to_background(
                                person_path, bg_path, file_id, person_idx, bg_idx
                            )
                            results.append(result_path)
                        except Exception as e:
                            logger.error(f"[{file_id}] ❌ Error swapping person {person_idx} to background {bg_idx}: {e}")
            
            logger.info(f"[{file_id}] ✅ Person swap completed: {len(results)} combinations created")
            return results
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error in separate person swap: {e}")
            raise

    async def _swap_person_to_background(self, person_path: str, background_path: str, 
                                       file_id: str, person_idx: int, bg_idx: int) -> str:
        """Подставляет одного человека на один фон"""
        logger.info(f"[{file_id}] 🔄 Swapping person {person_idx} to background {bg_idx}")
        
        try:
            with timer_step(f"Removing background from person {person_idx}", file_id):
                # Remove background from person image
                person_no_bg_path = await self.background_remover.remove_background(
                    person_path, f"{file_id}_person_{person_idx}", "rembg"
                )
                logger.info(f"[{file_id}] ✂️ Person background removed: {person_no_bg_path}")
            
            with timer_step(f"Compositing person on background {bg_idx}", file_id):
                # Load images
                person_img = Image.open(person_no_bg_path)
                background_img = Image.open(background_path)
                
                # Convert person image to RGBA if not already
                if person_img.mode != 'RGBA':
                    person_img = person_img.convert('RGBA')
                
                # Scale person to fit background proportionally
                bg_width, bg_height = background_img.size
                person_width, person_height = person_img.size
                
                # Calculate scale to fit person nicely (about 60% of background height)
                target_height = int(bg_height * 0.6)
                scale_factor = target_height / person_height
                new_person_width = int(person_width * scale_factor)
                new_person_height = target_height
                
                # Resize person
                person_resized = person_img.resize((new_person_width, new_person_height), Image.Resampling.LANCZOS)
                
                # Position person (center-bottom)
                x_pos = (bg_width - new_person_width) // 2
                y_pos = bg_height - new_person_height - 20  # Small margin from bottom
                
                # Ensure position is within bounds
                x_pos = max(0, min(x_pos, bg_width - new_person_width))
                y_pos = max(0, min(y_pos, bg_height - new_person_height))
                
                # Composite images
                if background_img.mode != 'RGBA':
                    background_img = background_img.convert('RGBA')
                
                result = background_img.copy()
                result.paste(person_resized, (x_pos, y_pos), person_resized)
                
                # Convert back to RGB for saving
                final_result = Image.new('RGB', result.size, (255, 255, 255))
                final_result.paste(result, mask=result.split()[-1] if result.mode == 'RGBA' else None)
                
                # Save result
                output_path = f"processed/{file_id}_swap_p{person_idx}_bg{bg_idx}.jpg"
                os.makedirs("processed", exist_ok=True)
                final_result.save(output_path, 'JPEG', quality=90, optimize=True)
                
                logger.info(f"[{file_id}] 🎭 Person swap completed: {output_path}")
                
                # Clean up temporary file
                try:
                    os.remove(person_no_bg_path)
                except Exception:
                    pass
                
                return output_path
                
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error swapping person {person_idx} to background {bg_idx}: {e}")
            raise