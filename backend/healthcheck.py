#!/usr/bin/env python3
import sys
import time
import requests

for attempt in range(5):
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            sys.exit(0)  # Success
        else:
            print(f"Health check failed with status {response.status_code}")
    except Exception as e:
        print(f"Attempt {attempt + 1}: Health check failed: {e}")
    time.sleep(5)

sys.exit(1)  # Fail after retries
