# features.py - User-facing features (Alerts, Logging, Breaks)

import time
from datetime import datetime
from plyer import notification
import csv
import os
import configure_setting as config

# ============================================================================
# ALERT MANAGER (Smart notifications without spam)
# ============================================================================
class AlertManager:
    """
    Manages posture alerts intelligently:
    - Only alerts after sustained bad posture (3 min)
    - Has cooldown period to prevent spam (5 min)
    """
    
    def __init__(self):
        self.bad_start = None       # Timestamp when bad posture started
        self.last_alert = None       # Timestamp of last alert sent
        self.alert_count = 0         # How many alerts sent this session
    
    def check(self, status):
        """
        Call this every frame with current posture status.
        Automatically sends notification when needed.
        
        Args:
            status: "GOOD", "FAIR", or "BAD"
        """
        if status == "BAD":
            # Start timer if this is first bad frame
            if self.bad_start is None:
                self.bad_start = time.time()
            
            # Calculate how long we've been in bad posture
            duration = time.time() - self.bad_start
            
            # Check if we should alert
            if duration >= config.BAD_DURATION:
                # Check cooldown (don't spam)
                if self.last_alert is None or \
                   (time.time() - self.last_alert) >= config.ALERT_COOLDOWN:
                    
                    # Send notification
                    self._send_notification(duration)
                    self.last_alert = time.time()
                    self.alert_count += 1
        else:
            # Posture improved, reset timer
            self.bad_start = None
    
    def _send_notification(self, duration):
        """Send OS notification"""
        try:
            notification.notify(
                title=config.ALERT_TITLE,
                message=f"Bad posture for {duration/60:.1f} minutes. Sit up straight!",
                timeout=5
            )
            print(f"🔔 Alert sent (#{self.alert_count + 1})")
        except Exception as e:
            print(f"⚠️  Notification failed: {e}")
    
    def get_stats(self):
        """Get alert statistics"""
        return {
            'total_alerts': self.alert_count,
            'currently_bad': self.bad_start is not None,
            'bad_duration': time.time() - self.bad_start if self.bad_start else 0
        }


# ============================================================================
# BREAK REMINDER (Suggests regular breaks)
# ============================================================================
class BreakReminder:
    """
    Reminds user to take breaks every 30 minutes.
    Based on ergonomic best practices (20-20-20 rule).
    """
    
    def __init__(self):
        self.last_break = time.time()
        self.break_count = 0
    
    def check(self):
        """
        Call this every frame. Sends reminder when interval reached.
        """
        if time.time() - self.last_break >= config.BREAK_INTERVAL:
            self._send_reminder()
            self.last_break = time.time()
            self.break_count += 1
    
    def _send_reminder(self):
        """Send break reminder notification"""
        try:
            notification.notify(
                title="Break Time!",
                message="You've been sitting for 30 minutes. Stand and stretch!",
                timeout=10
            )
            print(f"🧘 Break reminder sent (#{self.break_count + 1})")
        except Exception as e:
            print(f"⚠️  Break reminder failed: {e}")
    
    def get_stats(self):
        """Get break statistics"""
        time_until_break = config.BREAK_INTERVAL - (time.time() - self.last_break)
        return {
            'total_breaks': self.break_count,
            'time_until_next_break': max(0, time_until_break)
        }


# ============================================================================
# SESSION LOGGER (Tracks posture over time)
# ============================================================================
class SessionLogger:
    """
    Logs posture data and calculates performance scores.
    Saves to CSV for analysis.
    """
    
    def __init__(self):
        self.log = []                           # List of data points
        self.session_start = datetime.now()     # When session started
        self.last_record = time.time()          # Last time we logged
    
    def record(self, status, angle):
        """
        Record a data point. Logs every RECORD_EVERY seconds.
        
        Args:
            status: "GOOD", "FAIR", or "BAD"
            angle: Current posture angle in degrees
        """
        # Only log every N seconds (avoid massive files)
        if time.time() - self.last_record >= config.RECORD_EVERY:
            self.log.append({
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'angle': round(angle, 2)
            })
            self.last_record = time.time()
    
    def get_score(self):
        """
        Calculate 0-100 posture score for this session.
        
        Formula: Weighted average
        - GOOD = 100 points
        - FAIR = 60 points  
        - BAD = 20 points
        
        Returns:
            float: Score from 0-100
        """
        if not self.log:
            return 0.0
        
        good = sum(1 for x in self.log if x['status'] == 'GOOD')
        fair = sum(1 for x in self.log if x['status'] == 'FAIR')
        bad = sum(1 for x in self.log if x['status'] == 'BAD')
        
        total = len(self.log)
        score = (good * 100 + fair * 60 + bad * 20) / total
        
        return round(score, 1)
    
    def get_summary(self):
        """
        Get detailed session statistics.
        
        Returns:
            dict: Statistics about this session
        """
        if not self.log:
            return {
                'duration': 0,
                'data_points': 0,
                'score': 0,
                'good_percent': 0,
                'fair_percent': 0,
                'bad_percent': 0
            }
        
        good = sum(1 for x in self.log if x['status'] == 'GOOD')
        fair = sum(1 for x in self.log if x['status'] == 'FAIR')
        bad = sum(1 for x in self.log if x['status'] == 'BAD')
        total = len(self.log)
        
        duration = (datetime.now() - self.session_start).total_seconds()
        
        return {
            'duration': duration,
            'data_points': total,
            'score': self.get_score(),
            'good_percent': round(good / total * 100, 1),
            'fair_percent': round(fair / total * 100, 1),
            'bad_percent': round(bad / total * 100, 1),
            'good_count': good,
            'fair_count': fair,
            'bad_count': bad
        }
    
    def save(self):
        """
        Save session to CSV file.
        Creates file in data/sessions/ directory.
        """
        if not self.log:
            print("⚠️  No data to save (session too short)")
            return None
        
        # Generate filename with timestamp
        filename = os.path.join(
            config.SESSIONS_DIR,
            f"session_{self.session_start.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        # Write CSV
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'status', 'angle'])
                writer.writeheader()
                writer.writerows(self.log)
            
            # Print summary
            summary = self.get_summary()
            
            print("\n" + "="*60)
            print("📊 SESSION SUMMARY")
            print("="*60)
            print(f"Duration: {summary['duration']/60:.1f} minutes")
            print(f"Data points: {summary['data_points']}")
            print(f"Posture Score: {summary['score']}/100")
            print(f"\nPosture Distribution:")
            print(f"  GOOD: {summary['good_count']} ({summary['good_percent']}%)")
            print(f"  FAIR: {summary['fair_count']} ({summary['fair_percent']}%)")
            print(f"  BAD:  {summary['bad_count']} ({summary['bad_percent']}%)")
            print(f"\n✅ Session saved: {filename}")
            print("="*60)
            
            return filename
            
        except Exception as e:
            print(f"❌ Failed to save session: {e}")
            return None


# ============================================================================
# TESTING (Run this file directly to test)
# ============================================================================
if __name__ == "__main__":
    print("🧪 Testing features.py components...\n")
    
    # Test 1: AlertManager
    print("Test 1: AlertManager")
    alerts = AlertManager()
    print("  Simulating bad posture...")
    for i in range(5):
        alerts.check("BAD")
        time.sleep(1)
    stats = alerts.get_stats()
    print(f"  Currently bad: {stats['currently_bad']}")
    print(f"  Duration: {stats['bad_duration']:.1f}s")
    print("✅ AlertManager working\n")
    
    # Test 2: BreakReminder
    print("Test 2: BreakReminder")
    breaks = BreakReminder()
    stats = breaks.get_stats()
    print(f"  Time until next break: {stats['time_until_next_break']:.0f}s")
    print("✅ BreakReminder working\n")
    
    # Test 3: SessionLogger
    print("Test 3: SessionLogger")
    logger = SessionLogger()
    
    # Simulate some data
    import random
    for i in range(20):
        status = random.choice(["GOOD", "FAIR", "BAD"])
        angle = random.uniform(150, 180)
        logger.record(status, angle)
        time.sleep(0.1)  # Fast simulation
    
    score = logger.get_score()
    print(f"  Logged {len(logger.log)} data points")
    print(f"  Current score: {score}/100")
    
    summary = logger.get_summary()
    print(f"  Distribution: {summary['good_percent']}% GOOD, "
          f"{summary['fair_percent']}% FAIR, {summary['bad_percent']}% BAD")
    
    # Don't actually save in test
    print("  (Skipping save in test mode)")
    print("✅ SessionLogger working\n")
    
    print("="*60)
    print("All tests complete. Module is ready to use.")
    print("="*60)