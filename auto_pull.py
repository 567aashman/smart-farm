import os
import time
import subprocess

print("Auto-pull daemon started...")
while True:
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=False)
    except Exception as e:
        print(f"Error pulling: {e}")
    time.sleep(15)
