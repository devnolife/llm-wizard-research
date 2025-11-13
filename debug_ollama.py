"""Debug Ollama API responses"""
import ollama

print("Testing Ollama client...")
client = ollama.Client(host="http://localhost:11434")

# Test 1: List models
print("\n1. Testing client.list():")
try:
    response = client.list()
    print(f"   Type: {type(response)}")
    print(f"   Content: {response}")
    
    if hasattr(response, '__dict__'):
        print(f"   Attributes: {response.__dict__}")
except Exception as e:
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Try generate
print("\n2. Testing client.generate():")
try:
    response = client.generate(
        model="glm-4.6:cloud",
        prompt="Say hello",
        stream=False
    )
    print(f"   Type: {type(response)}")
    print(f"   Content: {response}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Direct HTTP call
print("\n3. Testing direct HTTP API:")
import requests
try:
    resp = requests.get("http://localhost:11434/api/tags")
    print(f"   Status: {resp.status_code}")
    print(f"   JSON: {resp.json()}")
except Exception as e:
    print(f"   Error: {e}")
