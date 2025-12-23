# posture_core.py - Detection + Analysis (The ML Brain)

import cv2
import mediapipe as mp
import math
import json
import time
import configure_setting

# ============================================================================
# POSE DETECTOR (Wraps MediaPipe)
# ============================================================================
class PoseDetector:
    """Detects human pose from camera frames"""
    
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            model_complexity=configure_setting.MODEL_COMPLEXITY,
            min_detection_confidence=configure_setting.DETECTION_CONFIDENCE
        )
    
    def detect(self, frame):
        """
        Takes a frame, returns landmarks (or None if no person detected)
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            landmarks: List of 33 body points, or None
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        
        if results.pose_landmarks:
            return results.pose_landmarks
        return None
    
    def draw_skeleton(self, frame, pose_landmarks):
        """
        Draw pose skeleton on the frame
        
        Args:
            frame: OpenCV image to draw on
            pose_landmarks: Landmarks from detect()
        """
        self.mp_drawing.draw_landmarks(
            frame,
            pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
        )


# ============================================================================
# POSTURE ANALYZER (Calculates angles & classifies)
# ============================================================================
class PostureAnalyzer:
    """Analyzes pose landmarks to classify posture quality"""
    
    def __init__(self, baseline=None):
        """
        Args:
            baseline: Optional dict with 'good_angle' from calibration
        """
        self.baseline = baseline
    
    def analyze(self, pose_landmarks):
        """
        Analyze posture from landmarks
        
        Args:
            pose_landmarks: MediaPipe pose landmarks object
            
        Returns:
            tuple: (status, angle) where status is "GOOD"/"FAIR"/"BAD"
        """
        landmarks = pose_landmarks.landmark
        
        # Get the 3 key points (ear, shoulder, hip)
        ear = landmarks[17]       # LEFT_EAR
        shoulder = landmarks[11]  # LEFT_SHOULDER
        hip = landmarks[23]       # LEFT_HIP
        
        # Calculate head-shoulder-hip angle
        angle = self._calculate_angle(ear, shoulder, hip)
        
        # Classify using baseline or fixed thresholds
        if self.baseline:
            good_threshold = self.baseline['good_angle'] - 10
            fair_threshold = self.baseline['good_angle'] - 20
        else:
            good_threshold = configure_setting.GOOD_ANGLE
            fair_threshold = configure_setting.FAIR_ANGLE
        
        if angle >= good_threshold:
            status = "GOOD"
        elif angle >= fair_threshold:
            status = "FAIR"
        else:
            status = "BAD"
        
        return status, angle
    
    def _calculate_angle(self, a, b, c):
        """
        Calculate angle at point b formed by points a-b-c
        
        Think: ear(a) -> shoulder(b) -> hip(c)
        Small angle = head leaning forward = bad posture
        
        Args:
            a, b, c: MediaPipe landmark objects with .x, .y, .z
            
        Returns:
            float: Angle in degrees
        """
        radians = math.atan2(c.y - b.y, c.x - b.x) - \
                  math.atan2(a.y - b.y, a.x - b.x)
        angle = abs(radians * 180.0 / math.pi)
        
        if angle > 180.0:
            angle = 360 - angle
        
        return angle


# ============================================================================
# CALIBRATION FUNCTIONS
# ============================================================================
def calibrate_user(duration=120):
    """
    User sits in GOOD posture, system learns their baseline angle.
    
    Args:
        duration: How long to observe (seconds)
        
    Returns:
        dict: {'good_angle': 175.2, 'tolerance': 10} or None if failed
    """
    print(f"\n🎯 Starting {duration}s calibration...")
    print("Sit in your BEST comfortable posture and stay still.\n")
    
    detector = PoseDetector()
    analyzer = PostureAnalyzer()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, configure_setting.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, configure_setting.CAMERA_HEIGHT)
    
    angles = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if not ret:
            continue
        
        pose_landmarks = detector.detect(frame)
        
        if pose_landmarks:
            _, angle = analyzer.analyze(pose_landmarks)
            angles.append(angle)
            
            # Visual feedback
            remaining = duration - (time.time() - start_time)
            cv2.putText(frame, f'Calibrating: {remaining:.0f}s remaining', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f'Current angle: {angle:.1f}°', (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, f'Samples collected: {len(angles)}', (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            detector.draw_skeleton(frame, pose_landmarks)
        else:
            cv2.putText(frame, 'No person detected - face camera!', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imshow('Calibration', frame)
        
        # Allow early exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n⚠️  Calibration cancelled by user")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Validate data
    if len(angles) < 50:
        print(f"❌ Not enough data collected ({len(angles)} samples)")
        print("   Need at least 50 samples. Try again with better lighting.")
        return None
    
    # Calculate baseline
    avg_angle = sum(angles) / len(angles)
    baseline = {
        'good_angle': avg_angle,
        'tolerance': 10.0,
        'samples': len(angles),
        'min_angle': min(angles),
        'max_angle': max(angles)
    }
    
    # Save to file
    with open('user_baseline.json', 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\n✅ Calibration complete!")
    print(f"   Your baseline angle: {baseline['good_angle']:.1f}°")
    print(f"   Samples collected: {baseline['samples']}")
    print(f"   Range: {baseline['min_angle']:.1f}° - {baseline['max_angle']:.1f}°")
    print(f"   Saved to: user_baseline.json\n")
    
    return baseline


def load_baseline():
    """
    Load previously saved baseline calibration
    
    Returns:
        dict: Baseline data or None if not found
    """
    try:
        with open('user_baseline.json', 'r') as f:
            baseline = json.load(f)
            return baseline
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print("⚠️  Corrupted baseline file. Run calibration again.")
        return None


# ============================================================================
# TESTING (Run this file directly to test components)
# ============================================================================
if __name__ == "__main__":
    print("🧪 Testing posture_core.py components...\n")
    
    # Test 1: Detector initialization
    print("Test 1: PoseDetector initialization")
    try:
        detector = PoseDetector()
        print("✅ PoseDetector created successfully\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    # Test 2: Analyzer initialization
    print("Test 2: PostureAnalyzer initialization")
    try:
        analyzer = PostureAnalyzer()
        print("✅ PostureAnalyzer created successfully\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    # Test 3: Baseline loading
    print("Test 3: Load baseline (if exists)")
    baseline = load_baseline()
    if baseline:
        print(f"✅ Baseline loaded: {baseline['good_angle']:.1f}°\n")
    else:
        print("⚠️  No baseline found (expected if not calibrated yet)\n")
    
    # Test 4: Quick camera test
    print("Test 4: Camera detection (5 seconds)")
    print("Press 'q' to skip...")
    
    cap = cv2.VideoCapture(0)
    detector = PoseDetector()
    analyzer = PostureAnalyzer()
    
    start = time.time()
    detected_count = 0
    
    while time.time() - start < 5:
        ret, frame = cap.read()
        if ret:
            pose_landmarks = detector.detect(frame)
            if pose_landmarks:
                detected_count += 1
                status, angle = analyzer.analyze(pose_landmarks)
                cv2.putText(frame, f'{status}: {angle:.1f}°', (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    if detected_count > 0:
        print(f"✅ Detection working! Detected person in {detected_count} frames\n")
    else:
        print("⚠️  No person detected. Check camera and lighting.\n")
    
    print("="*60)
    print("All tests complete. Module is ready to use.")
    print("="*60)