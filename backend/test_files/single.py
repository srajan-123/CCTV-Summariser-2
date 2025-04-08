import cv2
import numpy as np
import time
import logging
from ultralytics import YOLO


YOLO_MODEL_PATH = 'yolov8n.pt'
YOLO_NAMES_PATH = 'coco.names'

# for frame subtraction
MOTION_THRESHOLD = 25                   # Pixel intensity difference threshold
MOTION_AREA_THRESHOLD = 5000            # Minimum number of changed pixels to consider as motion

# for object detection
RECORD_TIMEOUT = 5                     # Time (in seconds) to wait after the last detection before stopping recording
CONFIDENCE_THRESHOLD = 0.5              # YOLO confidence threshold for detections


def load_yolo_model():
    model = YOLO(YOLO_MODEL_PATH)
    return model

def load_classes():
    with open(YOLO_NAMES_PATH, "r") as f:
        classes = [line.strip() for line in f.readlines()]
    return classes

def detect_motion(prev_gray, curr_gray):
    # Compute absolute difference between consecutive frames
    diff = cv2.absdiff(prev_gray, curr_gray)
    _, thresh = cv2.threshold(diff, MOTION_THRESHOLD, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=2)
    non_zero_count = cv2.countNonZero(dilated)
    return non_zero_count > MOTION_AREA_THRESHOLD, dilated

def detect_objects_yolo(model, frame, classes, conf_threshold=CONFIDENCE_THRESHOLD):
    # Define relevant objects for surveillance
    relevant_classes = {"person", "bicycle", "car", "motorcycle", "bus", "truck"}

    results = model(frame)
    detected_objects = []
    for result in results:
        for box in result.boxes:
            confidence = float(box.conf)
            if confidence >= conf_threshold:
                class_id = int(box.cls[0])
                label = classes[class_id]

                # Only keep objects that are in the relevant list
                if label in relevant_classes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detected_objects.append({
                        'label': label,
                        'confidence': confidence,
                        'box': [int(x1), int(y1), int(x2), int(y2)]
                    })
    return detected_objects

def main():
    logging.basicConfig(level=logging.INFO)
    
    yolo_model = load_yolo_model()
    classes = load_classes()
    demo_video_path = './test1.mp4'
    
    # Open the video stream (change 0 to a video file path if needed)
    cap = cv2.VideoCapture(demo_video_path)
    if not cap.isOpened():
        logging.error("Error opening video stream or file")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 25  # default fallback
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Variables for motion detection and recording management
    recording = False
    last_detection_time = None
    out = None

    ret, frame = cap.read()
    if not ret:
        logging.error("Failed to read the initial frame.")
        cap.release()
        return

    prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Main processing loop
    while ret:
        ret, frame = cap.read()
        if not ret:
            break

        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion_detected, diff_frame = detect_motion(prev_gray, curr_gray)
        prev_gray = curr_gray

        if motion_detected:
            logging.info("Motion detected.")
            # Run object detection on the frame when motion is detected
            detected_objects = detect_objects_yolo(yolo_model, frame, classes)
            if detected_objects:
                labels = [obj['label'] for obj in detected_objects]
                logging.info(f"Detected objects: {labels}")
                last_detection_time = time.time()
                if not recording:
                    recording = True
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter('output_summary.mp4', fourcc, fps, (width, height))
                    logging.info("Started recording.")
            else:
                logging.info("Motion detected, but no objects of interest found.")

        if recording:
            out.write(frame)
            # Stop recording if no objects have been detected for RECORD_TIMEOUT seconds
            if last_detection_time and (time.time() - last_detection_time) > RECORD_TIMEOUT:
                logging.info("No objects detected for threshold time. Stopping recording.")
                recording = False
                out.release()
                out = None

        # Optional: display the frame and motion mask (for debugging)
        cv2.imshow("Live Feed", frame)
        cv2.imshow("Motion Mask", diff_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up
    cap.release()
    if out is not None:
        out.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
