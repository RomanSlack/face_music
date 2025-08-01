#!/usr/bin/env python3
"""
Simple audio test to check if MP3 playback works
"""

import subprocess
import os
import time

def test_audio():
    # Test file path
    audio_file = "/home/roman/face_music/song3.mp3"
    
    print(f"Testing audio file: {audio_file}")
    
    # Check if file exists
    if not os.path.exists(audio_file):
        print(f"ERROR: File not found: {audio_file}")
        return
    
    print(f"File exists: {os.path.getsize(audio_file)} bytes")
    
    # Try different audio players
    players = [
        ["mpg123", audio_file],
        ["ffplay", "-nodisp", "-autoexit", audio_file],
        ["aplay", audio_file],
        ["paplay", audio_file]
    ]
    
    for player in players:
        try:
            print(f"Trying {player[0]}...")
            result = subprocess.run([player[0], "--version"], capture_output=True, timeout=2)
            if result.returncode == 0:
                print(f"{player[0]} is available")
                
                # Try to play for 3 seconds
                print(f"Playing with {player[0]}...")
                proc = subprocess.Popen(player, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                time.sleep(3)
                proc.terminate()
                print(f"Stopped {player[0]}")
                return
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(f"{player[0]} not available")
            continue
    
    print("No suitable audio player found. Installing mpg123...")
    try:
        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "-y", "mpg123"], check=True)
        
        # Try again with mpg123
        print("Playing with newly installed mpg123...")
        proc = subprocess.Popen(["mpg123", audio_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)
        proc.terminate()
        print("Audio test complete")
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to install mpg123: {e}")

if __name__ == "__main__":
    test_audio()