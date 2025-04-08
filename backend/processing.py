import os
import cv2
import numpy as np
import time
import logging
import uuid
from ultralytics import YOLO
from typing import Tuple
from config import (
    YOLO_MODEL_PATH, YOLO_NAMES_PATH, MOTION_THRESHOLD, MOTION_AREA_THRESHOLD,
    RECORD_TIMEOUT, CONFIDENCE_THRESHOLD, OUTPUT_DIR
)

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

def process_video(video_path: str) -> Tuple[list, str]:
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
    last_detection_video_time = None  # Video timestamp (in seconds) when detection last occurred
    logs = []
    recorded_frames = []  # To accumulate all frames to be recorded
    frame_index = 0

    ret, frame = cap.read()
    if not ret:
        cap.release()
        raise Exception("Failed to read initial frame")
    prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    while ret:
        ret, frame = cap.read()
        if not ret:
            break
        frame_index += 1
        current_video_time = frame_index / fps  # Video time in seconds
        
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion_detected, diff_frame = detect_motion(prev_gray, curr_gray)
        prev_gray = curr_gray
        
        if motion_detected:
            detected_objects = detect_objects_yolo(yolo_model, frame, classes)
            if detected_objects:
                # Use video timestamp for logs
                formatted_time = time.strftime('%H:%M:%S', time.gmtime(current_video_time))
                # logs.append(f"{formatted_time} - Detected objects: {[obj['label'] for obj in detected_objects]}")
                last_detection_video_time = current_video_time
                if not recording:
                    logs.append(f"{formatted_time} - Started recording")
                    recording = True
                recorded_frames.append(frame.copy())
            else:
                if recording:
                    recorded_frames.append(frame.copy())
        else:
            if recording:
                # Check inactivity using video time rather than system time
                if last_detection_video_time is not None and (current_video_time - last_detection_video_time) > RECORD_TIMEOUT:
                    formatted_time = time.strftime('%H:%M:%S', time.gmtime(current_video_time))
                    logs.append(f"{formatted_time} - Stopped recording")
                    recording = False
                else:
                    recorded_frames.append(frame.copy())
    
    cap.release()
    
    if recording:
        # In case recording is still active at the end of the video
        formatted_time = time.strftime('%H:%M:%S', time.gmtime(current_video_time))
        logs.append(f"{formatted_time} - Stopped recording")
    
    # Write accumulated frames to final output video
    output_filename = os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex}_summary.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))
    for f in recorded_frames:
        out.write(f)
    out.release()
    
    return logs, output_filename
