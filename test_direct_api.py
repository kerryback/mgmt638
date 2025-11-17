"""Test the direct API approach by submitting a request."""

import httpx
import time

# Wait for server to be ready
print("Waiting for server to start...")
time.sleep(2)

# Submit request for PE histogram
print("\nSubmitting request for 'PE' histogram...")
print("This will take 2-5 minutes...")

response = httpx.post(
    "http://localhost:8002/generate",
    data={"characteristic": "PE"},
    timeout=300.0,
    follow_redirects=True
)

print(f"\nStatus code: {response.status_code}")

if response.status_code == 200:
    if "Success" in response.text or "success" in response.text:
        print("✅ SUCCESS! Histogram was generated.")
    else:
        print("Response received but checking for errors...")
        if "error" in response.text.lower():
            print("❌ Error found in response")
            # Print first 1000 chars of response
            print(response.text[:1000])
        else:
            print("Response looks good")
else:
    print(f"❌ Failed with status code: {response.status_code}")
    print(response.text[:500])
