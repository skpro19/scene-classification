from fastapi import FastAPI, HTTPException, UploadFile, File
import uvicorn
import os
import sys
import logging
import cv2
import numpy as np
from pyzed import sl
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the current directory (where api.py is located)
CURRENT_DIR = Path(__file__).parent.absolute()
OUTPUT_DIR = CURRENT_DIR / "output"
TEMP_DIR = CURRENT_DIR / "temp"

# Create necessary directories
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="SVO Service",
    description="A FastAPI service for extracting images from SVO files",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SVO Service is running"}

@app.get("/status")
async def status_check():
    """Check if the server is up and running"""
    return {
        "status": "healthy",
        "service": "svo-service",
        "version": "1.0.0",
        "output_directory": str(OUTPUT_DIR),
        "temp_directory": str(TEMP_DIR)
    }

@app.post("/extract-svo-images")
async def extract_svo_images(file: UploadFile = File(...)):
    """
    Extract images from an SVO file and save them to the output folder
    
    Args:
        file: The .svo file to extract images from
        
    Returns:
        dict: Information about the extracted images
    """
    # Check if file is an SVO file
    if not file.filename.lower().endswith('.svo'):
        raise HTTPException(
            status_code=400, 
            detail="File must be a .svo file"
        )
    
    # Save uploaded file temporarily
    temp_file_path = TEMP_DIR / file.filename
    try:
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        logger.info(f"Saved uploaded file to: {temp_file_path}")
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Error processing uploaded file")
    
    # Create output directory for extracted images
    output_dir = OUTPUT_DIR / f"extracted_images_{file.filename.replace('.svo', '')}"
    output_dir.mkdir(exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    
    try:
        # Initialize ZED camera
        zed = sl.Camera()
        
        # Set configuration parameters
        init_params = sl.InitParameters()
        init_params.set_from_svo_file(str(temp_file_path))
        init_params.svo_real_time_mode = False
        
        # Open the SVO file
        err = zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to open SVO file: {err}"
            )
        
        # Get SVO information
        svo_position = zed.get_svo_position()
        svo_number_of_frames = zed.get_svo_number_of_frames()
        logger.info(f"SVO file has {svo_number_of_frames} frames")
        
        # Initialize image containers
        left_image = sl.Mat()
        right_image = sl.Mat()
        depth_image = sl.Mat()
        
        extracted_count = 0
        frame_interval = max(1, svo_number_of_frames // 100)  # Extract ~100 frames
        
        # Extract frames
        while zed.get_svo_position() < svo_number_of_frames - 1:
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                # Extract left image
                zed.retrieve_image(left_image, sl.VIEW.LEFT)
                
                # Extract right image
                zed.retrieve_image(right_image, sl.VIEW.RIGHT)
                
                # Extract depth image
                zed.retrieve_image(depth_image, sl.VIEW.DEPTH)
                
                # Save images
                frame_number = zed.get_svo_position()
                if frame_number % frame_interval == 0:
                    # Save left image
                    left_filename = output_dir / f"left_frame_{frame_number:06d}.png"
                    cv2.imwrite(str(left_filename), left_image.get_data())
                    
                    # Save right image
                    right_filename = output_dir / f"right_frame_{frame_number:06d}.png"
                    cv2.imwrite(str(right_filename), right_image.get_data())
                    
                    # Save depth image
                    depth_filename = output_dir / f"depth_frame_{frame_number:06d}.png"
                    cv2.imwrite(str(depth_filename), depth_image.get_data())
                    
                    extracted_count += 1
                    
                    logger.info(f"Extracted frame {frame_number}/{svo_number_of_frames}")
            else:
                break
        
        # Close the camera
        zed.close()
        
        # Clean up uploaded file
        try:
            os.remove(temp_file_path)
            logger.info(f"Cleaned up temporary file: {temp_file_path}")
        except Exception as e:
            logger.warning(f"Could not remove temporary file {temp_file_path}: {e}")
        
        return {
            "message": "Images extracted successfully",
            "total_frames": svo_number_of_frames,
            "extracted_frames": extracted_count,
            "output_directory": str(output_dir),
            "file_types": ["left", "right", "depth"],
            "format": "PNG"
        }
        
    except Exception as e:
        logger.error(f"Error extracting images from SVO: {e}")
        # Clean up uploaded file
        try:
            os.remove(temp_file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error extracting images: {str(e)}")

if __name__ == "__main__":
    logger.info(f"Starting SVO Service on port 8000")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Temp directory: {TEMP_DIR}")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for production
        log_level="info",
        access_log=True
    ) 