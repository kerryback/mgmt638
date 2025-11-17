"""Test Claude Agent SDK with cli_path parameter."""
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions

async def test_agent():
    options = ClaudeAgentOptions(
        cli_path=r"C:\Users\kerry\.local\bin\claude.exe"
    )

    print("Testing Claude Agent SDK with cli_path...")
    print("="*60)

    async for message in query(prompt="What is 2 + 2?", options=options):
        print(f"\n{type(message).__name__}:")
        print(message)

    print("\n" + "="*60)
    print("Test completed!")

if __name__ == "__main__":
    anyio.run(test_agent)
