"""
Rice Database Characteristic Histogram Agent - Gradio Web App

This Gradio app uses the Claude Agent SDK to:
1. Accept a user-specified financial characteristic
2. Query the Rice Database to get the most recent value for each stock
3. Calculate the characteristic if needed (e.g., financial ratios)
4. Display a histogram of the characteristic values

Usage:
    python rice_histogram_gradio.py
"""

import gradio as gr
import subprocess
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a financial data analysis expert specializing in the Rice Data Portal.

Your task is to:
1. Accept a financial characteristic from the user (e.g., "PE ratio", "ROE", "market cap", "debt-to-equity")
2. Determine which Rice database table(s) contain this data or the data needed to calculate it
3. Write and execute SQL queries to get the MOST RECENT value of this characteristic for each stock
4. If the characteristic needs to be calculated (e.g., current ratio = current assets / current liabilities), calculate it
5. Create a histogram showing the distribution of this characteristic across all stocks
6. Provide summary statistics (mean, median, min, max, standard deviation)

CRITICAL RULES FOR RICE DATABASE QUERIES:

1. All date columns are VARCHAR and must be cast to DATE for comparisons
2. To get the most recent data:
   - For DAILY table: WHERE date = (SELECT MAX(date) FROM daily)
   - For SF1 table: Use the most recent reportperiod for each ticker
   - For SEP table: WHERE date = (SELECT MAX(date) FROM sep)

3. Always use python-dotenv to load RICE_ACCESS_TOKEN from .env file
4. Filter out NULL values and extreme outliers before plotting
5. Use matplotlib to create a clean, professional histogram
6. Label axes clearly and include a title

Remember: The user will provide the characteristic name. You need to figure out how to get it!
"""


def run_agent(characteristic: str):
    """Run the Claude agent to generate a histogram."""

    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        return None, "Error: ANTHROPIC_API_KEY not found in .env file", 0.0

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
    options = ClaudeCodeOptions(
        system_prompt=SYSTEM_PROMPT,
        max_turns=15,
        allowed_tools=["Bash", "Read", "Write", "Skill"],
    )

    prompt = '''Please create a histogram showing the distribution of {characteristic} across all stocks in the Rice database.

Steps:
1. Use the rice-data-query skill to query the database
2. Get the MOST RECENT value for each stock
3. Clean the data (remove nulls, extreme outliers)
4. Create a professional histogram with matplotlib
5. Include summary statistics
6. Save the plot as '{characteristic.replace(' ', '_').lower()}_histogram.png'

Remember to use the .env file to load RICE_ACCESS_TOKEN!
'''

    agent_output = []
    total_cost = 0.0

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    agent_output.append(block.text)
                    print(f"[AGENT] {{block.text[:100]}}...", file=sys.stderr)
        elif isinstance(message, ResultMessage):
            total_cost = message.total_cost_usd
            print(f"[RESULT] Cost: ${{total_cost}}", file=sys.stderr)

    result = {{"output": agent_output, "cost": total_cost}}
    print("AGENT_RESULT:" + json.dumps(result))

if __name__ == "__main__":
    asyncio.run(main())
"""

    # Write the script to a temporary file
    script_path = Path("_temp_gradio_agent.py")
    script_path.write_text(agent_script, encoding='utf-8')

    try:
        print(f"Starting agent for: {characteristic}")

        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )

        # Parse the result
        agent_output = []
        total_cost = 0.0

        for line in result.stdout.split('\n'):
            if line.startswith('AGENT_RESULT:'):
                data = json.loads(line.replace('AGENT_RESULT:', ''))
                agent_output = data['output']
                total_cost = data['cost']
                break

        # Look for the histogram file
        histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
        histogram_path = Path(histogram_filename)

        if histogram_path.exists():
            print(f"Success! Found histogram: {histogram_path}")
            output_text = "\n\n".join(agent_output) if agent_output else "Agent completed successfully"
            return str(histogram_path), output_text, total_cost
        else:
            error_msg = f"Histogram file not found: {histogram_filename}\n\nStderr:\n{result.stderr[:1000]}"
            return None, error_msg, total_cost

    except subprocess.TimeoutExpired:
        return None, "Agent timed out after 5 minutes", 0.0

    except Exception as e:
        import traceback
        error_msg = f"Error: {type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        return None, error_msg, 0.0

    finally:
        # Clean up temp file
        if script_path.exists():
            script_path.unlink()


def generate_histogram(characteristic: str):
    """Gradio interface function."""
    if not characteristic or not characteristic.strip():
        return None, "Please enter a financial characteristic", "$0.00"

    histogram_path, output, cost = run_agent(characteristic.strip())

    if histogram_path:
        return histogram_path, output, f"${cost:.4f}"
    else:
        return None, output, f"${cost:.4f}"


# Create Gradio interface
with gr.Blocks(title="Rice Database Histogram Generator", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📊 Rice Database Histogram Generator")
    gr.Markdown("AI-powered financial characteristic visualization using Claude Agent SDK")

    with gr.Row():
        with gr.Column():
            gr.Markdown("""
            ### How it works:
            Enter any financial characteristic and the AI agent will:
            - Determine which database tables to query
            - Retrieve the most recent data for each stock
            - Calculate ratios if needed
            - Create a professional histogram with statistics

            ### Example characteristics:
            - PE ratio
            - Market capitalization
            - Return on Equity (ROE)
            - Debt-to-equity ratio
            - Book-to-market ratio
            """)

    with gr.Row():
        characteristic_input = gr.Textbox(
            label="Financial Characteristic",
            placeholder="e.g., PE ratio, ROE, market cap...",
            lines=1
        )

    with gr.Row():
        generate_btn = gr.Button("🚀 Generate Histogram", variant="primary", size="lg")

    with gr.Row():
        with gr.Column():
            output_image = gr.Image(label="Histogram", type="filepath")
        with gr.Column():
            output_text = gr.Textbox(label="Agent Output", lines=15)
            cost_text = gr.Textbox(label="API Cost", lines=1)

    generate_btn.click(
        fn=generate_histogram,
        inputs=[characteristic_input],
        outputs=[output_image, output_text, cost_text]
    )

    gr.Markdown("""
    ---
    **Note:** This may take 2-5 minutes for database queries and analysis.
    """)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("ERROR: ANTHROPIC_API_KEY not found in .env file")
        print("Please add your API key from: https://console.anthropic.com/")
        sys.exit(1)

    print("Starting Gradio app...")
    print("Open your browser to: http://localhost:7860")
    demo.launch(server_port=7860, share=False)
