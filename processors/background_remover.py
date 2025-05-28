import os
import logging
from contextlib import contextmanager
import time

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

# Lazy import для rembg
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

class BackgroundRemover:
    """Класс для удаления фона с изображений"""
    
    def __init__(self):
        pass
        
    async def remove_background(self, input_path: str, file_id: str, method: str = "rembg") -> str:
        """Remove background from image using specified method"""
        logger.info(f"[{file_id}] 🎨 Starting background removal with method: {method}")
        logger.info(f"[{file_id}] 📁 Input file: {input_path}")
        
        try:
            if method == "rembg":
                return await self._remove_background_rembg(input_path, file_id)
            elif method == "lbm":
                return await self._remove_background_lbm(input_path, file_id)
            else:
                raise ValueError(f"Unknown background removal method: {method}")
                
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error removing background with method {method}: {e}")
            raise

    async def _remove_background_rembg(self, input_path: str, file_id: str) -> str:
        """Remove background using rembg library"""
        logger.info(f"[{file_id}] 🔧 Using rembg method for background removal")
        
        try:
            with timer_step("Reading input image", file_id):
                with open(input_path, 'rb') as f:
                    input_data = f.read()
                logger.info(f"[{file_id}] 📖 Read {len(input_data)} bytes from input file")
            
            with timer_step("Loading rembg library", file_id):
                remove_func = get_rembg()
                logger.info(f"[{file_id}] ✅ rembg library loaded successfully")
            
            with timer_step("AI background removal processing", file_id):
                output_data = remove_func(input_data)
                logger.info(f"[{file_id}] 🤖 AI processing complete, output size: {len(output_data)} bytes")
            
            with timer_step("Saving result", file_id):
                output_path = f"processed/{file_id}_no_bg.png"
                os.makedirs("processed", exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(output_data)
                logger.info(f"[{file_id}] 💾 Result saved to: {output_path}")
            
            logger.info(f"[{file_id}] ✅ Background removed successfully with rembg: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error removing background with rembg: {e}")
            raise

    async def _remove_background_lbm(self, input_path: str, file_id: str) -> str:
        """Remove background using jasperai/LBM_relighting method"""
        logger.info(f"[{file_id}] 🔧 Using LBM method for background removal")
        
        try:
            with timer_step("Loading image for LBM processing", file_id):
                from PIL import Image
                import io
                
                # Load image
                img = Image.open(input_path)
                logger.info(f"[{file_id}] 📖 Loaded image: {img.size}")
                
                # Convert to bytes for API
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
            
            with timer_step("LBM API processing", file_id):
                # Placeholder for LBM API call
                # В реальном проекте здесь был бы вызов к jasperai API
                logger.warning(f"[{file_id}] ⚠️ LBM method not fully implemented - using rembg as fallback")
                return await self._remove_background_rembg(input_path, file_id)
                
        except Exception as e:
            logger.error(f"[{file_id}] ❌ Error removing background with LBM: {e}")
            raise