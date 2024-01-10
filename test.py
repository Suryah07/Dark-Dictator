#55105KB
#without cv2 ->5823KB
import os
print("importing")
import httpimport
httpimport.CONFIG.read('profile.ini')
with httpimport.pypi_repo(profile='sam'):
    import cv2

def capture_webcam():
    webcam = cv2.VideoCapture(0)
    webcam.set(cv2.CAP_PROP_EXPOSURE, 40)

    # Check if the webcam is available
    if not webcam.isOpened():
        print("No webcam available")
        return
    
    ret, frame = webcam.read()

    # Check if the webcam was able to capture a frame
    if not ret:
        print("Failed to read frame from webcam")
        return

    webcam.release()

    # Save the frame to a file
    if platform == "win32" or platform == "darwin" or platform == "linux" or platform == "linux2":
        is_success, im_buf_arr = cv2.imencode("webcam.png", frame)
        if is_success:
            with open('webcam.png', 'wb') as f:
                f.write(im_buf_arr.tobytes())
        else:
            print("Failed to save webcam image")


print("hi")