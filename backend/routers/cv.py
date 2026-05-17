import os
import shutil
import tempfile
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException
from backend.services.plate_ocr_service import PlateOCRService
from backend.services.drowsiness_service import DrowsinessService

logger = logging.getLogger("drivelegal.routers.cv")
router = APIRouter(prefix="/api/v1/cv", tags=["Computer Vision"])

plate_service = PlateOCRService()
drowsiness_service = DrowsinessService()

@router.post("/plate-ocr", summary="Extract Indian vehicle registration plate from image")
async def extract_plate(file: UploadFile = File(...)):
    """
    Accepts an uploaded image of a vehicle number plate and extracts the plate number.
    Falls back gracefully to simulated/default output if OCR fails or libraries are missing.
    """
    try:
        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            result = plate_service.extract_plate(tmp_path)
            return result
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.exception("Error in plate-ocr endpoint: %s", e)
        raise HTTPException(status_code=500, detail=f"Plate OCR processing error: {str(e)}")

@router.post("/drowsiness", summary="Analyze face frame for eye-closure drowsiness detection")
async def detect_drowsiness(file: UploadFile = File(...)):
    """
    Analyzes an uploaded face image using MediaPipe FaceMesh EAR to determine drowsiness.
    """
    try:
        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            result = drowsiness_service.analyze_frame(tmp_path)
            return result
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.exception("Error in drowsiness endpoint: %s", e)
        raise HTTPException(status_code=500, detail=f"Drowsiness analysis error: {str(e)}")
