#!/usr/bin/env python3
"""
FacePlay Trigger - Simple Facial Expression Music Trigger
Uses webcam to detect facial expressions and trigger media playback.
"""

import cv2
import numpy as np
import subprocess
import threading
import time
import os
import webbrowser
import json

class FacePlayTrigger:
    def __init__(self):
        # Initialize OpenCV face detection (more reliable than MediaPipe)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
        
        # Audio player process
        self.audio_process = None
        
        # Camera
        self.cap = cv2.VideoCapture(0)
        
        # Expression detection state
        self.last_trigger_time = {"eyebrow_raise": 0, "wink": 0, "smile": 0}
        self.trigger_cooldown = 3.0  # seconds
        
        # Load config
        self.load_config()
        
        # State tracking for simple expressions
        self.previous_face_area = 0
        self.eye_blink_counter = 0
        self.last_eye_count = 2
        self.frame_count = 0
        self.wink_frames = 0
        self.smile_frames = 0
        self.face_area_history = []
        self.movement_cooldown = 0
        
        # Music state tracking
        self.music_file = None
        self.is_smiling = False
        self.is_paused = False
        self.last_smile_check = 0
        self.smile_check_interval = 1.5  # Check every 1.5 seconds
        
    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # Default config
            self.config = {
                "expressions": {
                    "eyebrow_raise": {
                        "action": "play_youtube",
                        "media_path": "https://www.youtube.com/watch?v=VlZdCpPXLns",
                        "description": "Face movement triggers YouTube video"
                    },
                    "wink": {
                        "action": "play_local",
                        "media_path": "default_music.mp3",
                        "description": "Wink triggers local music"
                    },
                    "smile": {
                        "action": "play_youtube", 
                        "media_path": "https://www.youtube.com/watch?v=DDQCO3Vykts",
                        "description": "Smile triggers YouTube video"
                    }
                },
                "settings": {
                    "detection_confidence": 0.7,
                    "expression_threshold": 0.15
                }
            }
    
    def detect_smile_state(self, face_gray, face_coords):
        """Detect if currently smiling (continuous state)"""
        x, y, w, h = face_coords
        roi_gray = face_gray[y:y+h, x:x+w]
        
        smiles = self.smile_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.7,
            minNeighbors=15,
            minSize=(25, 25)
        )
        
        # Return True if smile detected
        return len(smiles) > 0
    
    def detect_wink(self, eyes):
        """Detect wink by tracking eye count changes - complete gesture only"""
        current_eye_count = len(eyes)
        
        # Look for pattern: 2 eyes -> 1 eye -> 2 eyes (complete wink)
        if self.last_eye_count == 2 and current_eye_count == 1:
            self.wink_frames += 1
        elif self.last_eye_count == 1 and current_eye_count == 2 and self.wink_frames > 0:
            # Complete wink detected - eyes reopened
            if 1 <= self.wink_frames <= 8:  # Quick wink gesture (not long blink)
                self.wink_frames = 0
                self.last_eye_count = current_eye_count
                return True
            self.wink_frames = 0
        elif current_eye_count == 2:
            # Reset if eyes are open for too long
            if self.wink_frames > 0:
                self.wink_frames = 0
            
        self.last_eye_count = current_eye_count
        return False
    
    def detect_smile(self, face_gray, face_coords):
        """Detect smile using Haar cascade - only trigger on smile start"""
        x, y, w, h = face_coords
        roi_gray = face_gray[y:y+h, x:x+w]
        
        smiles = self.smile_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.8,
            minNeighbors=20,
            minSize=(25, 25)
        )
        
        if len(smiles) > 0:
            self.smile_frames += 1
            # Only trigger on initial smile detection, not continuous
            if self.smile_frames == 3:  # Trigger only once when smile starts
                return True
        else:
            self.smile_frames = 0  # Reset when not smiling
            
        return False
    
    def trigger_action(self, expression_name):
        """Trigger the action associated with an expression"""
        current_time = time.time()
        if current_time - self.last_trigger_time[expression_name] < self.trigger_cooldown:
            return
        
        self.last_trigger_time[expression_name] = current_time
        
        expression_config = self.config["expressions"].get(expression_name)
        if not expression_config:
            return
        
        action = expression_config["action"]  
        media_path = expression_config["media_path"]
        
        print(f"Triggered: {expression_name} -> {expression_config['description']}")
        
        if action == "play_youtube":
            threading.Thread(target=self.play_youtube, args=(media_path,)).start()
        elif action == "play_local":
            threading.Thread(target=self.play_local_audio, args=(media_path,)).start()
    
    def play_youtube(self, url):
        """Open YouTube video in browser"""
        try:
            webbrowser.open(url)
            print(f"Opening YouTube video: {url}")
        except Exception as e:
            print(f"Error opening YouTube video: {e}")
    
    def load_music(self, file_path):
        """Load music file for continuous playback"""
        if os.path.exists(file_path):
            self.music_file = file_path
            print(f"Music loaded: {file_path}")
            return True
        else:
            print(f"Audio file not found: {file_path}")
            return False
    
    def play_music(self):
        """Start/resume music playback"""
        if not self.music_file:
            return
            
        if self.audio_process is None:
            # Start new playback with mpg123 (loops indefinitely)
            try:
                self.audio_process = subprocess.Popen(
                    ["mpg123", "--loop", "-1", self.music_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.is_paused = False
                print("Music playing")
            except FileNotFoundError:
                print("mpg123 not found. Installing...")
                try:
                    subprocess.run(["sudo", "apt", "install", "-y", "mpg123"], check=True)
                    self.play_music()  # Try again
                except subprocess.CalledProcessError:
                    print("Failed to install mpg123")
        elif self.is_paused:
            # Resume by sending SIGCONT
            self.audio_process.send_signal(18)  # SIGCONT
            self.is_paused = False
            print("Music resumed")
    
    def pause_music(self):
        """Pause music playback"""
        if self.audio_process and not self.is_paused:
            # Pause by sending SIGSTOP
            self.audio_process.send_signal(19)  # SIGSTOP
            self.is_paused = True
            print("Music paused")
    
    def stop_music(self):
        """Stop music playback completely"""
        if self.audio_process:
            self.audio_process.terminate()
            self.audio_process = None
            self.is_paused = False
            print("Music stopped")
    
    def run(self):
        """Main application loop"""
        print("FacePlay Trigger started! Press 'q' to quit.")
        
        # Load the music file
        smile_config = self.config["expressions"].get("smile")
        if smile_config and smile_config.get("action") == "play_local":
            music_path = smile_config.get("media_path")
        else:
            # Fallback to eyebrow_raise config
            eyebrow_config = self.config["expressions"].get("eyebrow_raise")
            if eyebrow_config and eyebrow_config.get("action") == "play_local":
                music_path = eyebrow_config.get("media_path")
            else:
                music_path = None
                
        if music_path:
            self.load_music(music_path)
        
        print("\nControls:")
        print("  - SMILE to play music")
        print("  - STOP SMILING (frown/neutral) to pause music")
        print("  - Music resumes where it left off")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Flip frame horizontally for selfie-view
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            for (x, y, w, h) in faces:
                # Draw rectangle around face
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                face_area = w * h
                roi_gray = gray[y:y+h, x:x+w]
                
                # Detect eyes within face region
                eyes = self.eye_cascade.detectMultiScale(
                    roi_gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(10, 10)
                )
                
                # Draw rectangles around eyes
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(frame, (x+ex, y+ey), (x+ex+ew, y+ey+eh), (0, 255, 0), 2)
                
                # Check smile state only every 1.5 seconds to reduce sensitivity
                current_time = time.time()
                if current_time - self.last_smile_check >= self.smile_check_interval:
                    self.last_smile_check = current_time
                    current_smile_state = self.detect_smile_state(gray, (x, y, w, h))
                    
                    # Handle music play/pause based on smile state
                    if current_smile_state and not self.is_smiling:
                        # Started smiling - start/resume music
                        self.is_smiling = True
                        self.play_music()
                    elif not current_smile_state and self.is_smiling:
                        # Stopped smiling - pause music
                        self.is_smiling = False
                        self.pause_music()
                
                # Display current state
                state_text = "PLAYING" if self.is_smiling else "PAUSED"
                expression_text = "SMILING" if self.is_smiling else "NOT SMILING"
                cv2.putText(frame, f"Music: {state_text}", (x, y-30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if self.is_smiling else (0, 0, 255), 2)
                cv2.putText(frame, expression_text, (x, y-50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                
                # Display eye count for debugging
                cv2.putText(frame, f"Eyes: {len(eyes)}", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Display frame
            cv2.imshow('FacePlay Trigger - Press Q to quit', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        self.stop_music()
        self.cap.release()
        cv2.destroyAllWindows()

def main():
    app = FacePlayTrigger()
    app.run()

if __name__ == "__main__":
    main()