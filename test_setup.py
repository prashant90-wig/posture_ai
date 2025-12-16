print("Testing ")

try:
    import cv2
    print("✅ OpenCV installed")
except:
    print("❌ OpenCV missing")

try:
    import mediapipe
    print("✅ MediaPipe installed")
except:
    print("❌ MediaPipe missing")

try:
    import numpy
    print("✅ NumPy installed")
except:
    print("❌ NumPy missing")

try:
    import pandas
    print("✅ Pandas installed")
except:
    print("❌ Pandas missing")

try:
    from plyer import notification
    print("✅ Plyer installed")
except:
    print("❌ Plyer missing")

print("\n🎯 If all show ✅, you're ready to code!")