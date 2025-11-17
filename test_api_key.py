"""
Test script to verify ANTHROPIC_API_KEY works by sending a simple query
"""

import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

def test_api_key():
    """Send a simple test query to verify the API key works."""

    api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in .env file")
        return False

    print(f"API key found: {api_key[:20]}...{api_key[-4:]}")
    print("\nSending test query to Anthropic API...")

    try:
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "What is 2 + 2? Just give me the number."}
            ]
        )

        response_text = message.content[0].text

        print(f"\nSUCCESS: API key is valid!")
        print(f"Response: {response_text}")
        print(f"Model: {message.model}")
        print(f"Usage: {message.usage.input_tokens} input tokens, {message.usage.output_tokens} output tokens")

        return True

    except anthropic.AuthenticationError as e:
        print(f"\nERROR: Authentication failed!")
        print(f"Error: {e}")
        return False

    except Exception as e:
        print(f"\nERROR: Error occurred!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_api_key()
