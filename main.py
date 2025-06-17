import cv2
import base64
import requests
import numpy as np
import time
import re
import threading

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llava:7b"

PROMPT = """Analyze the person in this image and estimate:
1. Age in format "Age: XX-XX years" (example: "Age: 18-25 years")
2. Gender as "Male" or "Female"
Respond ONLY in this format:
Age: XX-XX years
Gender: Male/Female"""

class RealTimeAnalyzer:
    def __init__(self):
        self.current_age = "Analyzing..."
        self.current_gender = "Analyzing..."
        self.latest_frame = None
        self.lock = threading.Lock()
        self.stop_thread = False

    def parse_output(self, output):
        age_range = "Unknown"
        gender = "Unknown"
        
        age_match = re.search(r"Age:\s*(\d+)\s*-\s*(\d+)\s*years", output, re.IGNORECASE)
        if age_match:
            age_range = f"{age_match.group(1)}-{age_match.group(2)}"
        
        gender_match = re.search(r"Gender:\s*(Male|Female)", output, re.IGNORECASE)
        if gender_match:
            gender = gender_match.group(1)
        
        return age_range, gender

    def analyze_frame(self, frame):
        _, img_encoded = cv2.imencode('.jpg', frame)
        image_base64 = base64.b64encode(img_encoded).decode('utf-8')

        payload = {
            "model": MODEL_NAME,
            "prompt": PROMPT,
            "images": [image_base64],
            "stream": False
        }

        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=5)
            if response.status_code == 200:
                output = response.json().get("response", "")
                age, gender = self.parse_output(output)
                with self.lock:
                    self.current_age = age
                    self.current_gender = gender
                print(f"Age: {age}, Gender: {gender}")
        except Exception as e:
            print(f"Analysis error: {str(e)}")

    def analysis_thread(self):
        while not self.stop_thread:
            if self.latest_frame is not None:
                frame = self.latest_frame.copy()
                self.analyze_frame(frame)
            time.sleep(0.1)  # Small sleep to prevent 100% CPU usage

def main():
    analyzer = RealTimeAnalyzer()
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    # Start analysis thread
    thread = threading.Thread(target=analyzer.analysis_thread)
    thread.daemon = True
    thread.start()

    cv2.namedWindow("Real-time Age/Gender Detection", cv2.WINDOW_NORMAL)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror the frame
            frame = cv2.flip(frame, 1)
            analyzer.latest_frame = frame
            
            # Get current results
            with analyzer.lock:
                current_age = analyzer.current_age
                current_gender = analyzer.current_gender
            
            # Display results
            cv2.putText(frame, f"Age: {current_age}", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Gender: {current_gender}", (20, 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Real-time Age/Gender Detection", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        analyzer.stop_thread = True
        thread.join()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()