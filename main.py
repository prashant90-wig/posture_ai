# main.py - AI Posture Monitor (Main Application)

import cv2
import time
import sys
import configure_setting as config
from posture_core import PoseDetector, PostureAnalyzer, load_baseline
from features import AlertManager, BreakReminder, SessionLogger


def print_banner():
    """Print startup banner"""
    print("\n" + "="*60)
    print("🤖 AI POSTURE MONITOR")
    print("="*60)
    print("Real-time posture detection using MediaPipe AI")
    print("="*60 + "\n")


def initialize_system():
    """
    Initialize all components and check system readiness.
    
    Returns:
        tuple: (baseline, detector, analyzer, alerts, breaks, logger)
    """
    print("🔧 Initializing system...")
    
    # Load user baseline (if calibrated)
    baseline = load_baseline()
    if baseline:
        print(f"✅ Loaded calibration: {baseline['good_angle']:.1f}° baseline")
    else:
        print("⚠️  No calibration found - using default thresholds")
        print("   Tip: Run 'python calibrate.py' for personalized detection\n")
    
    # Initialize components
    try:
        detector = PoseDetector()
        analyzer = PostureAnalyzer(baseline)
        alerts = AlertManager()
        breaks = BreakReminder()
        logger = SessionLogger()
        print("✅ All components initialized\n")
        return baseline, detector, analyzer, alerts, breaks, logger
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        print("   Check that all dependencies are installed:")
        print("   pip install opencv-python mediapipe plyer")
        sys.exit(1)


def setup_camera():
    """
    Initialize camera with configured settings.
    
    Returns:
        cv2.VideoCapture: Camera object or None if failed
    """
    print("📹 Starting camera...")
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Cannot access camera")
        print("   Possible fixes:")
        print("   - Check camera is connected")
        print("   - Close other apps using camera")
        print("   - Try camera index 1: VideoCapture(1)")
        return None
    
    # Configure camera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    
    # Test frame
    ret, frame = cap.read()
    if not ret:
        print("❌ Camera opened but cannot read frames")
        cap.release()
        return None
    
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"✅ Camera ready: {actual_width}x{actual_height}\n")
    
    return cap


def display_ui(frame, pose_landmarks, status, angle, score, fps, detector):
    """
    Draw all UI elements on frame.
    
    Args:
        frame: OpenCV image to draw on
        pose_landmarks: MediaPipe landmarks (or None)
        status: "GOOD", "FAIR", or "BAD"
        angle: Current posture angle
        score: Session score (0-100)
        fps: Current frames per second
        detector: PoseDetector instance for drawing skeleton
    """
    if pose_landmarks:
        # Draw skeleton
        detector.draw_skeleton(frame, pose_landmarks)
        
        # Choose color based on status
        if status == "GOOD":
            color = config.COLOR_GOOD
        elif status == "FAIR":
            color = config.COLOR_FAIR
        else:
            color = config.COLOR_BAD
        
        # Display posture status (large)
        cv2.putText(frame, f'Posture: {status}', (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
        
        # Display angle (medium)
        cv2.putText(frame, f'Angle: {angle:.1f}°', (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Display score (medium, yellow)
        cv2.putText(frame, f'Score: {score}/100', (10, 140),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    else:
        # No person detected warning
        cv2.putText(frame, 'No person detected', (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, config.COLOR_BAD, 2)
        cv2.putText(frame, 'Face the camera', (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, config.COLOR_BAD, 2)
    
    # Always show FPS (top, white)
    cv2.putText(frame, f'FPS: {fps:.1f}', (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, config.COLOR_TEXT, 2)
    
    # Show controls hint (bottom right)
    cv2.putText(frame, "Press 'q' to quit", (frame.shape[1] - 200, frame.shape[0] - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, config.COLOR_TEXT, 1)


def main_loop(cap, detector, analyzer, alerts, breaks, logger):
    """
    Main application loop - processes frames until user quits.
    
    Args:
        cap: OpenCV VideoCapture
        detector: PoseDetector instance
        analyzer: PostureAnalyzer instance
        alerts: AlertManager instance
        breaks: BreakReminder instance
        logger: SessionLogger instance
    """
    print("🚀 Monitoring started!")
    print("   - Sit naturally in front of camera")
    print("   - Press 'q' to stop and save session")
    print("   - Window will show real-time feedback\n")
    
    fps_list = []
    frame_count = 0
    
    try:
        while cap.isOpened():
            frame_start = time.time()
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to grab frame")
                break
            
            frame_count += 1
            
            # 1. DETECT: Get pose landmarks
            pose_landmarks = detector.detect(frame)
            
            # Default values
            status = "UNKNOWN"
            angle = 0
            score = logger.get_score()
            
            if pose_landmarks:
                # 2. ANALYZE: Classify posture
                status, angle = analyzer.analyze(pose_landmarks)
                
                # 3. ALERT: Check if notification needed
                alerts.check(status)
                
                # 4. BREAKS: Check if break reminder needed
                breaks.check()
                
                # 5. LOG: Record data
                logger.record(status, angle)
                
                # Update score
                score = logger.get_score()
            
            # Calculate FPS
            frame_time = time.time() - frame_start
            fps = 1 / frame_time if frame_time > 0 else 0
            fps_list.append(fps)
            
            # 6. DISPLAY: Show everything
            display_ui(frame, pose_landmarks, status, angle, score, fps, detector)
            
            # Show window
            cv2.imshow('AI Posture Monitor', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n👋 Stopping...")
                break
            
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user...")
    except Exception as e:
        print(f"\n❌ Error during monitoring: {e}")
    finally:
        # Calculate average FPS
        if fps_list:
            avg_fps = sum(fps_list) / len(fps_list)
            
            print(f"\n⚡ Performance: {avg_fps:.1f} FPS average")
            
            if avg_fps < config.MIN_FPS:
                print(f"⚠️  FPS below minimum ({config.MIN_FPS})")
                print("   Suggestions:")
                print("   - Close other applications")
                print("   - Lower resolution in config.py")
                print("   - Improve lighting (helps detection speed)")


def cleanup_and_save(cap, logger):
    """
    Clean up resources and save session data.
    
    Args:
        cap: OpenCV VideoCapture to release
        logger: SessionLogger to save
    """
    print("\n🧹 Cleaning up...")
    
    # Release camera
    if cap:
        cap.release()
    
    # Close windows
    cv2.destroyAllWindows()
    
    # Save session
    print("\n💾 Saving session data...")
    logger.save()


def main():
    """Main entry point"""
    # Print banner
    print_banner()
    
    # Initialize system
    baseline, detector, analyzer, alerts, breaks, logger = initialize_system()
    
    # Setup camera
    cap = setup_camera()
    if cap is None:
        print("\n❌ Cannot start without camera. Exiting.")
        sys.exit(1)
    
    # Run main loop
    try:
        main_loop(cap, detector, analyzer, alerts, breaks, logger)
    finally:
        # Always cleanup, even if error
        cleanup_and_save(cap, logger)
    
    print("\n✅ Session complete. Thank you for using AI Posture Monitor!\n")


if __name__ == "__main__":
    main()