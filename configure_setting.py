# Configuration settings for posture monitoring application

# Camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
MIN_FPS = 8  

# MediaPipe
MODEL_COMPLEXITY = 0  # 0=Lite (for 4GB RAM), 1=Full, 2=Heavy
DETECTION_CONFIDENCE = 0.5

# Posture thresholds (degrees)
GOOD_ANGLE = 170  # Upright
FAIR_ANGLE = 160  # Slight slouch
# Below FAIR_ANGLE = BAD

# Alerts
BAD_DURATION = 180  # Alert after 3 min of bad posture
ALERT_COOLDOWN = 300  # 5 mi0n between alerts
BREAK_INTERVAL = 1800  # Suggest break every 30 min

# Logging
RECORD_EVERY = 5  # Log data every 5 seconds

# Display colors (BGR format)
COLOR_GOOD = (0, 255, 0)  # Green
COLOR_FAIR = (0, 165, 255)  # Orange
COLOR_BAD = (0, 0, 255)  # Red

# File paths and directories
import os
DATA_DIR = "data"
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)