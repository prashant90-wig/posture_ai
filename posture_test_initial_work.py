"""
AI Posture Correction System
Single-file version for rapid development and testing

Author: Prashant
Date: December 2024
"""

import cv2
import mediapipe as mp
import time
import math
import json
import csv
from datetime import datetime
from plyer import notification

# ============================================================
# CONFIGURATION
# ============================================================
class Config:
    # Camera settings
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    
    # Posture thresholds (degrees)
    GOOD_POSTURE_ANGLE = 170
    FAIR_POSTURE_ANGLE = 160
    
    # Alert settings
    BAD_POSTURE_DURATION = 180  # 3 minutes in seconds
    ALERT_COOLDOWN = 300  # 5 minutes in seconds
    BREAK_REMINDER_INTERVAL = 1800  # 30 minutes
    
    # Logging
    LOG_INTERVAL = 5  # Record every 5 seconds
    
    # MediaPipe settings
    MODEL_COMPLEXITY = 0  # Lite model for performance
    MIN_DETECTION_CONFIDENCE = 0.5
    MIN_TRACKING_CONFIDENCE = 0.5


# ============================================================
# CORE FUNCTIONS
# ============================================================

def calculate_angle(a, b, c):
    """Calculate angle between three points (a-b-c)"""
    radians = math.atan2(c.y - b.y, c.x - b.x) - \
              math.atan2(a.y - b.y, a.x - b.x)
    angle = abs(radians * 180.0 / math.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle


def check_posture(landmarks, mp_pose, baseline=None):
    """
    Analyze posture based on body landmarks
    Args:
        landmarks: MediaPipe pose landmarks
        mp_pose: MediaPipe pose object
        baseline: Optional calibration baseline
    Returns:
        (status, angle) tuple
    """
    try:
        # Get key points
        ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR.value]
        shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
        
        # Calculate angle
        angle = calculate_angle(ear, shoulder, hip)
        
        # Use baseline if available (adaptive mode)
        if baseline:
            good_threshold = baseline['good_angle'] - baseline['tolerance']
            fair_threshold = baseline['good_angle'] - 20
            
            if angle > good_threshold:
                return "GOOD", angle
            elif angle > fair_threshold:
                return "FAIR", angle
            else:
                return "BAD", angle
        
        # Use fixed thresholds (default mode)
        else:
            if angle > Config.GOOD_POSTURE_ANGLE:
                return "GOOD", angle
            elif angle > Config.FAIR_POSTURE_ANGLE:
                return "FAIR", angle
            else:
                return "BAD", angle
                
    except Exception as e:
        return "UNKNOWN", 0


def send_notification(title, message):
    """Send desktop notification"""
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=5
        )
        return True
    except Exception as e:
        print(f"⚠️  Notification failed: {e}")
        return False


def calculate_session_score(log_data):
    """
    Calculate 0-100 posture score from session data
    Formula: (Good×100 + Fair×60 + Bad×20) / Total
    """
    if not log_data:
        return 0
    
    good = sum(1 for entry in log_data if entry['status'] == 'GOOD')
    fair = sum(1 for entry in log_data if entry['status'] == 'FAIR')
    bad = sum(1 for entry in log_data if entry['status'] == 'BAD')
    
    total = len(log_data)
    score = (good * 100 + fair * 60 + bad * 20) / total
    
    return round(score, 1)


def save_session(log_data, start_time):
    """Save session data to CSV file"""
    if not log_data:
        return None
    
    filename = f"session_{start_time.strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'status', 'angle'])
            writer.writeheader()
            writer.writerows(log_data)
        
        score = calculate_session_score(log_data)
        print(f"\n✅ Session saved: {filename}")
        print(f"📊 Posture Score: {score}/100")
        return filename
    except Exception as e:
        print(f"⚠️  Could not save session: {e}")
        return None


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    # Initialize MediaPipe
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    pose = mp_pose.Pose(
        model_complexity=Config.MODEL_COMPLEXITY,
        min_detection_confidence=Config.MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=Config.MIN_TRACKING_CONFIDENCE
    )
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
    
    # Session tracking
    session_start = datetime.now()
    session_log = []
    
    # Timing variables
    fps_list = []
    frame_count = 0
    bad_posture_start = None
    last_alert_time = None
    last_log_time = time.time()
    break_reminder_time = time.time()
    
    # Baseline (TODO: Load from calibration)
    baseline = None  # Set to None for fixed thresholds
    
    print("="*60)
    print("🎯 AI POSTURE CORRECTION SYSTEM")
    print("="*60)
    print("Camera starting... Press 'Q' to quit")
    print("")
    
    while cap.isOpened():
        start = time.time()
        ret, frame = cap.read()
        
        if not ret:
            break
        
        frame_count += 1
        
        # Process frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)
        
        status = "NO DETECTION"
        angle = 0
        color = (128, 128, 128)
        
        # If person detected
        if results.pose_landmarks:
            # Draw skeleton
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
            )
            
            # Check posture
            status, angle = check_posture(results.pose_landmarks.landmark, mp_pose, baseline)
            
            # Set color
            if status == "GOOD":
                color = (0, 255, 0)
            elif status == "FAIR":
                color = (0, 165, 255)
            elif status == "BAD":
                color = (0, 0, 255)
            
            # Track bad posture duration
            if status == "BAD":
                if bad_posture_start is None:
                    bad_posture_start = time.time()
                else:
                    duration = time.time() - bad_posture_start
                    
                    # Alert after threshold
                    if duration > Config.BAD_POSTURE_DURATION:
                        now = time.time()
                        if last_alert_time is None or (now - last_alert_time) > Config.ALERT_COOLDOWN:
                            send_notification(
                                "⚠️ Posture Alert",
                                f"Bad posture for {duration/60:.1f} min. Sit up!"
                            )
                            last_alert_time = now
            else:
                bad_posture_start = None
            
            # Log data every 5 seconds
            if time.time() - last_log_time > Config.LOG_INTERVAL:
                session_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'status': status,
                    'angle': round(angle, 1)
                })
                last_log_time = time.time()
        
        # Break reminder
        if time.time() - break_reminder_time > Config.BREAK_REMINDER_INTERVAL:
            send_notification("Break Time!", "You've been sitting for 30 min. Stand up!")
            break_reminder_time = time.time()
        
        # Calculate FPS
        fps = 1 / (time.time() - start)
        fps_list.append(fps)
        avg_fps = sum(fps_list) / len(fps_list)
        
        # Display UI
        cv2.putText(frame, f'FPS: {fps:.1f}', 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        cv2.putText(frame, f'Posture: {status}', 
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        
        if angle > 0:
            cv2.putText(frame, f'Angle: {angle:.1f}°', 
                        (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show score
        if session_log:
            score = calculate_session_score(session_log)
            cv2.putText(frame, f'Score: {score}/100', 
                        (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Bad posture timer
        if bad_posture_start:
            duration = time.time() - bad_posture_start
            cv2.putText(frame, f'Bad posture: {duration:.0f}s', 
                        (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.putText(frame, "Press 'Q' to quit", 
                    (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow('AI Posture Correction', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Save session
    save_session(session_log, session_start)
    
    # Final summary
    print("\n" + "="*60)
    print("📊 SESSION SUMMARY")
    print("="*60)
    print(f"Duration: {(datetime.now() - session_start).seconds} seconds")
    print(f"Average FPS: {sum(fps_list)/len(fps_list):.1f}")
    print(f"Data points logged: {len(session_log)}")
    print("="*60)


if __name__ == "__main__":
    main()