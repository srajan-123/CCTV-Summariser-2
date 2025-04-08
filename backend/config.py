import os

# Configuration constants
YOLO_MODEL_PATH = './yolo/yolov8n.pt'
YOLO_NAMES_PATH = './yolo/coco.names'

MOTION_THRESHOLD = 25                   # Pixel intensity difference threshold for frame subtraction
MOTION_AREA_THRESHOLD = 5000            # Minimum number of changed pixels to consider as motion
RECORD_TIMEOUT = 3                      # Stop recording after 5 seconds of inactivity
CONFIDENCE_THRESHOLD = 0.5              # YOLO confidence threshold

OUTPUT_DIR = "./output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
