"""
Test LLM Integration with Ollama
Quick test to verify GLM model connection and generation
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_ollama_connection():
    """Test basic Ollama connectivity"""
    import httpx
    
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "glm-4.6:cloud")
    
    print("=" * 60)
    print("🔍 Testing Ollama LLM Integration")
    print("=" * 60)
    print(f"\n📍 Ollama URL: {base_url}")
    print(f"🤖 Model: {model}")
    
    # Test 1: Check Ollama is running
    print("\n[1/4] Checking Ollama service...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                print("   ✅ Ollama service is running")
                models = response.json().get("models", [])
                print(f"   📦 Available models: {len(models)}")
                for m in models:
                    print(f"      - {m['name']} ({m['size'] // (1024**3):.1f} GB)")
            else:
                print(f"   ❌ Ollama returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Cannot connect to Ollama: {e}")
        return False
    
    # Test 2: Check model availability
    print(f"\n[2/4] Checking model '{model}'...")
    model_exists = any(m['name'] == model for m in models)
    if model_exists:
        print(f"   ✅ Model '{model}' is available")
    else:
        print(f"   ⚠️  Model '{model}' not found")
        print(f"   Available: {[m['name'] for m in models]}")
        return False
    
    # Test 3: Test GLMInterface
    print("\n[3/4] Testing GLMInterface class...")
    try:
        from src.llm.glm_interface import GLMInterface
        
        llm = GLMInterface()
        health = await llm.health_check()
        
        if health["status"] == "healthy":
            print("   ✅ GLMInterface initialized successfully")
            print(f"   📊 Models available: {health['available_models']}")
        else:
            print(f"   ❌ Health check failed: {health}")
            return False
    except Exception as e:
        print(f"   ❌ GLMInterface error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Test text generation
    print("\n[4/4] Testing text generation...")
    try:
        test_prompt = "What is machine learning? Answer in one sentence."
        print(f"   📝 Prompt: {test_prompt}")
        print("   ⏳ Generating response...")
        
        # GLMInterface.generate() is synchronous, not async
        response = llm.generate(
            prompt=test_prompt,
            max_tokens=100,
            temperature=0.7
        )
        
        print(f"\n   🤖 Response:\n   {response}\n")
        print("   ✅ Text generation successful!")
        
    except Exception as e:
        print(f"   ❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! LLM integration is working!")
    print("=" * 60)
    return True


async def test_with_different_models():
    """Test with different available models"""
    models_to_test = [
        "glm-4.6:cloud",
        "llama3.2:latest",
        "smollm2:135m"
    ]
    
    print("\n🔄 Testing Multiple Models...")
    print("=" * 60)
    
    for model_name in models_to_test:
        print(f"\n🤖 Testing model: {model_name}")
        os.environ["OLLAMA_MODEL"] = model_name
        
        try:
            from src.llm.glm_interface import GLMInterface
            llm = GLMInterface()
            
            response = await llm.generate(
                prompt="Say 'Hello' in one word.",
                max_tokens=10,
                temperature=0.1
            )
            print(f"   ✅ {model_name}: {response.strip()}")
        except Exception as e:
            print(f"   ❌ {model_name} failed: {e}")
    
    print("\n" + "=" * 60)


async def main():
    """Run all tests"""
    success = await test_ollama_connection()
    
    if success:
        print("\n🎯 Want to test other models? (y/n)")
        # Uncomment below to enable interactive testing
        # choice = input().strip().lower()
        # if choice == 'y':
        #     await test_with_different_models()
    else:
        print("\n⚠️  Please fix the issues above and try again.")
        print("\nTroubleshooting tips:")
        print("1. Check if Ollama is running: systemctl status ollama")
        print("2. Verify model name: ollama list")
        print("3. Update .env with correct OLLAMA_MODEL")
        print("4. Test manually: ollama run glm-4.6:cloud 'Hello'")


if __name__ == "__main__":
    asyncio.run(main())
