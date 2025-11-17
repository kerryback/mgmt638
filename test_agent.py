"""
Test script to verify Claude Agent SDK works
"""

import asyncio
import os
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock

load_dotenv()

# Ensure Claude CLI is in PATH
claude_bin_path = os.path.expanduser('~/.local/bin')
if claude_bin_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{claude_bin_path};{os.environ.get('PATH', '')}"

async def test_agent():
    """Test the agent with a simple query."""

    print("Testing Claude Agent SDK...")
    print(f"ANTHROPIC_API_KEY set: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
    print(f"Claude CLI path: {claude_bin_path}")
    print(f"PATH: {os.environ.get('PATH')[:200]}...")
    print()

    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant.",
        max_turns=2,
        allowed_tools=["Bash"],
    )

    prompt = "What is 2 + 2? Just give me the number."

    print(f"Sending prompt: {prompt}")
    print()

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Agent response: {block.text}")
            elif isinstance(message, ResultMessage):
                print(f"Total cost: ${message.total_cost_usd:.4f}")

        print("\n✅ Test successful!")

    except Exception as e:
        print(f"\n❌ Test failed!")
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())
