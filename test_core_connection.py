# filepath: test_core_connection.py
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('CORE_API_KEY')
BASE_URL = "https://api.core.ac.uk/v3"

print(f"🔑 API Key: {API_KEY[:10]}...{API_KEY[-5:] if API_KEY else 'NOT SET'}")
print(f"🌐 Testing connection to: {BASE_URL}")

def test_with_retry(max_retries=3):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    for attempt in range(max_retries):
        try:
            print(f"\n🔄 Attempt {attempt + 1}/{max_retries}...")
            
            response = requests.get(
                f"{BASE_URL}/search/works",
                headers=headers,
                params={"q": "covid", "limit": 1},  # Query lebih sederhana
                timeout=30
            )
            
            print(f"✅ Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response: {data}")
                print("\n✨ Connection SUCCESS!")
                return True
            elif response.status_code == 401:
                print("\n❌ INVALID API KEY!")
                return False
            elif response.status_code == 403:
                print("\n❌ API KEY FORBIDDEN - Check quota/permissions")
                return False
            elif response.status_code == 500:
                print(f"⚠️ Server Error 500 - Retrying in 2s...")
                time.sleep(2)
            else:
                print(f"⚠️ Unexpected status: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("\n❌ TIMEOUT")
        except requests.exceptions.ConnectionError as e:
            print(f"\n❌ CONNECTION ERROR: {e}")
            return False
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
    
    print("\n❌ All attempts failed")
    return False

try:
    test_with_retry()
except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
