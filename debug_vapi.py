#!/usr/bin/env python

# Debug Vapi API
import os
import sys
import requests
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'omniflow.backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from omniflow.utils.config import settings
from omniflow.utils.vapi_client import get_default_vapi_config

def debug_vapi_api():
    print("🔍 Debugging Vapi API")
    print("=" * 50)
    
    api_key = settings.VAPI_API_KEY
    print(f"🔑 API Key: {api_key}")
    
    # Test our exact configuration
    print("\n📋 Testing OmniFlow configuration...")
    config = get_default_vapi_config()
    print(f"Config: {json.dumps(config, indent=2)}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "https://api.vapi.ai/assistant",
            headers=headers,
            json=config
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 400:
            print(f"Error details: {response.json()}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_vapi_api()
