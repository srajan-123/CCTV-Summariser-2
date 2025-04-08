import os
import cv2
import numpy as np
import time
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import shutil
import uuid
from concurrent.futures import ProcessPoolExecutor

# Configuration
YOLO_MODEL_PATH = './yolo/yolov8n.pt'  
YOLO_NAMES_PATH = './yolo/coco.names'

MOTION_THRESHOLD = 25                   # pixel intensity difference threshold for frame subtraction
MOTION_AREA_THRESHOLD = 5000            # minimum number of changed pixels to consider as motion
RECORD_TIMEOUT = 5                      # stop recording after 5 seconds of inactivity
CONFIDENCE_THRESHOLD = 0.5              # YOLO confidence threshold

OUTPUT_DIR = "./output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Helper Functions
def load_yolo_model():
    model = YOLO(YOLO_MODEL_PATH)
    return model

def load_classes():
    with open(YOLO_NAMES_PATH, "r") as f:
        classes = [line.strip() for line in f.readlines()]
    return classes

def detect_motion(prev_gray, curr_gray):
    diff = cv2.absdiff(prev_gray, curr_gray)
    _, thresh = cv2.threshold(diff, MOTION_THRESHOLD, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=2)
    non_zero_count = cv2.countNonZero(dilated)
    return non_zero_count > MOTION_AREA_THRESHOLD, dilated

def detect_objects_yolo(model, frame, classes, conf_threshold=CONFIDENCE_THRESHOLD):
    relevant_classes = {"person", "bicycle", "car", "motorcycle", "bus", "truck"}
    results = model(frame)
    detected_objects = []
    for result in results:
        for box in result.boxes:
            confidence = float(box.conf)
            if confidence >= conf_threshold:
                class_id = int(box.cls[0])
                label = classes[class_id]
                if label in relevant_classes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detected_objects.append({
                        'label': label,
                        'confidence': confidence,
                        'box': [int(x1), int(y1), int(x2), int(y2)]
                    })
    return detected_objects

# --------------------------- Main Processing Function ---------------------------
def process_video(video_path: str) -> (list, str):
    logging.basicConfig(level=logging.INFO)
    yolo_model = load_yolo_model()
    classes = load_classes()
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception("Error opening video file")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    recording = False
    last_detection_time = None
    out = None
    logs = []
    
    ret, frame = cap.read()
    if not ret:
        cap.release()
        raise Exception("Failed to read initial frame")
    prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Create an output file name
    output_filename = os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex}_summary.mp4")
    
    while ret:
        ret, frame = cap.read()
        if not ret:
            break
        
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion_detected, diff_frame = detect_motion(prev_gray, curr_gray)
        prev_gray = curr_gray
        
        if motion_detected:
            detected_objects = detect_objects_yolo(yolo_model, frame, classes)
            if detected_objects:
                labels = [obj['label'] for obj in detected_objects]
                logs.append(f"{time.strftime('%H:%M:%S')} - Detected objects: {labels}")
                last_detection_time = time.time()
                if not recording:
                    recording = True
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))
                    logs.append(f"{time.strftime('%H:%M:%S')} - Started recording")
        
        if recording:
            out.write(frame)
            if last_detection_time and (time.time() - last_detection_time) > RECORD_TIMEOUT:
                logs.append(f"{time.strftime('%H:%M:%S')} - No objects detected for {RECORD_TIMEOUT} seconds. Stopping recording.")
                recording = False
                out.release()
                out = None
        
    cap.release()
    if out is not None:
        out.release()
    
    return logs, output_filename

# --------------------------- API Setup with FastAPI ---------------------------
app = FastAPI()

# Allow CORS from frontend domain (adjust origin as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-video")
async def process_video_endpoint(file: UploadFile = File(...)):
    try:
        # Save uploaded video to a temporary file
        input_filename = os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex}_{file.filename}")
        with open(input_filename, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # For large videos, you might use parallel processing / chunking here.
        # For simplicity, we call the processing function directly.
        logs, summary_path = process_video(input_filename)
        
        # You may remove the input file after processing.
        os.remove(input_filename)
        
        return JSONResponse(content={
            "logs": logs,
            "summary_video": summary_path  # Client can later request this file via another endpoint
        })
    except Exception as e:
        logging.error(f"Error processing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-video")
async def download_video(video_path: str):
    if os.path.exists(video_path):
        return FileResponse(video_path, media_type='video/mp4', filename="summary.mp4")
    else:
        raise HTTPException(status_code=404, detail="Video not found")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
