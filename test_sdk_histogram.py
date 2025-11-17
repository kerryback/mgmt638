"""Test the SDK-based histogram app."""
import httpx
import time

print("Waiting 2 seconds for server...")
time.sleep(2)

print("\nTesting SDK histogram generator with 'market cap'")
print("="*60)

try:
    with httpx.stream("GET", "http://localhost:8006/generate_stream?characteristic=market cap", timeout=300.0) as response:
        print(f"Status: {response.status_code}\n")

        for line in response.iter_lines():
            if line.startswith("data: "):
                data = line[6:]
                print(data)

except Exception as e:
    print(f"\nError: {type(e).__name__}: {e}")
