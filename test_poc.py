"""Quick test of the PoC endpoint."""
import httpx
import time

print("Waiting 2 seconds for server to be fully ready...")
time.sleep(2)

print("\nTesting the /generate_stream endpoint...")
print("Requesting histogram for 'market cap'")
print("\n" + "="*60)

try:
    with httpx.stream("GET", "http://localhost:8004/generate_stream?characteristic=market cap", timeout=300.0) as response:
        print(f"Status: {response.status_code}\n")

        for line in response.iter_lines():
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                print(data)

except Exception as e:
    print(f"\nError: {type(e).__name__}: {e}")
