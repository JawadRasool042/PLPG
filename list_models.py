#!/usr/bin/env python3
import requests
import os

api_key = 'AIzaSyBqruzvus6CZ_6xQRWkhjHZkrzXPUXGQac'
url = f'https://generativelanguage.googleapis.com/v1/models?key={api_key}'

response = requests.get(url, timeout=15)
print(f'Status: {response.status_code}')
data = response.json()

if 'models' in data:
    print('Available models:')
    for model in data['models'][:10]:
        name = model.get('name', 'unknown')
        display_name = model.get('displayName', '')
        print(f"  {name} - {display_name}")
else:
    print("Response:", data)
