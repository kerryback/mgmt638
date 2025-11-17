"""Test the subprocess approach to running Claude Agent SDK on Windows."""

import subprocess
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a financial data analysis expert specializing in the Rice Data Portal.

Your task is to:
1. Query the Rice Database for PE ratio data
2. Get the MOST RECENT value for each stock
3. Create a histogram showing the distribution
4. Save as 'pe_histogram.png'

Use the rice-data-query skill to query the database.
Use python-dotenv to load RICE_ACCESS_TOKEN from .env file.
"""

def test_subprocess_agent():
    """Test running the agent in a subprocess."""

    characteristic = "PE"

    # Create a Python script to run the agent
    agent_script = f"""
import asyncio
import sys
import json
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, ResultMessage, TextBlock
from dotenv import load_dotenv

load_dotenv()

# Set Windows event loop policy
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

SYSTEM_PROMPT = '''{SYSTEM_PROMPT}'''

async def main():
    print("[DEBUG] Starting agent...", file=sys.stderr)

    options = ClaudeCodeOptions(
        system_prompt=SYSTEM_PROMPT,
        max_turns=15,
        allowed_tools=["Bash", "Read", "Write", "Skill"],
    )

    prompt = '''Please create a histogram showing the distribution of {characteristic} across all stocks in the Rice database.

Steps:
1. Use the rice-data-query skill to query the database for PE ratios
2. Get the MOST RECENT value for each stock
3. Clean the data (remove nulls, extreme outliers)
4. Create a professional histogram with matplotlib
5. Include summary statistics
6. Save the plot as '{characteristic.lower()}_histogram.png'

Remember to use the .env file to load RICE_ACCESS_TOKEN!
'''

    agent_output = []
    total_cost = 0.0

    print("[DEBUG] Starting query...", file=sys.stderr)

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    agent_output.append(block.text)
                    print(f"[AGENT] {{block.text[:100]}}...", file=sys.stderr)
        elif isinstance(message, ResultMessage):
            total_cost = message.total_cost_usd
            print(f"[RESULT] Cost: ${{total_cost}}", file=sys.stderr)

    print("[DEBUG] Query complete", file=sys.stderr)

    result = {{"output": agent_output, "cost": total_cost}}
    print("AGENT_RESULT:" + json.dumps(result))

if __name__ == "__main__":
    asyncio.run(main())
"""

    # Write the script to a temporary file
    script_path = Path("_test_subprocess.py")
    script_path.write_text(agent_script, encoding='utf-8')

    try:
        print(f"Starting subprocess test for: {characteristic}")
        print("This may take 2-5 minutes...")

        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )

        print(f"\nReturn code: {result.returncode}")

        print("\n=== STDOUT ===")
        print(result.stdout[:2000] if result.stdout else "(empty)")

        print("\n=== STDERR ===")
        print(result.stderr[:2000] if result.stderr else "(empty)")

        # Parse the result
        agent_output = []
        total_cost = 0.0

        for line in result.stdout.split('\n'):
            if line.startswith('AGENT_RESULT:'):
                data = json.loads(line.replace('AGENT_RESULT:', ''))
                agent_output = data['output']
                total_cost = data['cost']
                print(f"\n✅ Successfully parsed agent result!")
                print(f"Output items: {len(agent_output)}")
                print(f"Total cost: ${total_cost}")
                break
        else:
            print("\n❌ No AGENT_RESULT found in output")

        # Look for the histogram file
        histogram_filename = f"{characteristic.lower()}_histogram.png"
        histogram_path = Path(histogram_filename)

        print(f"\nLooking for: {histogram_path.absolute()}")
        print(f"Exists: {histogram_path.exists()}")

        if histogram_path.exists():
            print(f"\n✅ SUCCESS! Histogram created: {histogram_path}")
            return True
        else:
            print(f"\n❌ FAILED: Histogram not found")
            return False

    except subprocess.TimeoutExpired:
        print("\n❌ FAILED: Agent timed out after 5 minutes")
        return False

    except Exception as e:
        import traceback
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

    finally:
        # Clean up temp file
        if script_path.exists():
            script_path.unlink()
            print(f"\nCleaned up temp file: {script_path}")


if __name__ == "__main__":
    success = test_subprocess_agent()
    sys.exit(0 if success else 1)
