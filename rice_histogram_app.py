"""
Rice Database Characteristic Histogram Agent - FastAPI Web App

This FastAPI app uses the Claude Agent SDK to:
1. Accept a user-specified financial characteristic
2. Query the Rice Database to get the most recent value for each stock
3. Calculate the characteristic if needed (e.g., financial ratios)
4. Display a histogram of the characteristic values

Usage:
    uvicorn rice_histogram_app:app --reload
    Then open: http://localhost:8000
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, ResultMessage, TextBlock
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Fix for Windows subprocess issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load environment variables from .env file
load_dotenv()

# Ensure Claude CLI is in PATH
claude_bin_path = os.path.expanduser('~/.local/bin')
if claude_bin_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{claude_bin_path};{os.environ.get('PATH', '')}"

app = FastAPI(title="Rice Database Histogram Generator")

# Create templates directory if it doesn't exist
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

# Create the HTML template
template_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Rice Database Histogram Generator</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 900px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .info-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 30px;
            border-radius: 5px;
        }
        .info-box h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .info-box ul {
            margin-left: 20px;
            color: #555;
        }
        form {
            margin-bottom: 30px;
        }
        label {
            display: block;
            margin-bottom: 10px;
            color: #333;
            font-weight: 600;
        }
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error {
            background: #fee;
            border-left: 4px solid #f44;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            color: #c33;
        }
        .success {
            background: #efe;
            border-left: 4px solid #4f4;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            color: #363;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Rice Database Histogram Generator</h1>
        <p class="subtitle">AI-powered financial characteristic visualization</p>

        {% if not api_key_set %}
        <div class="error">
            <strong>⚠️ Configuration Error</strong><br>
            ANTHROPIC_API_KEY not found in .env file.<br>
            Please add your API key from <a href="https://console.anthropic.com/" target="_blank">console.anthropic.com</a>
        </div>
        {% else %}

        <div class="info-box">
            <h3>How it works:</h3>
            <p>Enter any financial characteristic and the AI agent will:</p>
            <ul>
                <li>Determine which database tables to query</li>
                <li>Retrieve the most recent data for each stock</li>
                <li>Calculate ratios if needed</li>
                <li>Create a professional histogram with statistics</li>
            </ul>
        </div>

        <div class="info-box">
            <h3>Example characteristics:</h3>
            <ul>
                <li>PE ratio</li>
                <li>Market capitalization</li>
                <li>Return on Equity (ROE)</li>
                <li>Debt-to-equity ratio</li>
                <li>Book-to-market ratio</li>
            </ul>
        </div>

        <form method="post" action="/generate" onsubmit="showLoading()">
            <label for="characteristic">What characteristic would you like to visualize?</label>
            <input type="text"
                   id="characteristic"
                   name="characteristic"
                   placeholder="e.g., PE ratio, ROE, market cap..."
                   required>
            <button type="submit">🚀 Generate Histogram</button>
        </form>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 20px; color: #667eea; font-weight: 600;">
                🤖 Agent is working... This may take 2-5 minutes for database queries and analysis.
            </p>
        </div>

        {% if error %}
        <div class="error">
            <strong>Error:</strong> {{ error }}
        </div>
        {% endif %}

        {% endif %}
    </div>

    <script>
        function showLoading() {
            document.getElementById('loading').classList.add('active');
        }
    </script>
</body>
</html>
"""

# Write the template with UTF-8 encoding
(templates_dir / "index.html").write_text(template_html, encoding='utf-8')

templates = Jinja2Templates(directory="templates")


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


def run_agent_sync(characteristic: str):
    """Run the agent synchronously in a separate thread with its own event loop."""
    import subprocess
    import json

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
        allowed_tools=["Bash", "Read", "Write"],
    )

    prompt = '''Please create a histogram showing the distribution of {characteristic} across all stocks in the Rice database.

Steps:
1. Determine which table(s) contain this characteristic (or the data to calculate it)
2. Query the Rice database to get the MOST RECENT value for each stock
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
        elif isinstance(message, ResultMessage):
            total_cost = message.total_cost_usd

    result = {{"output": agent_output, "cost": total_cost}}
    print("AGENT_RESULT:" + json.dumps(result))

if __name__ == "__main__":
    asyncio.run(main())
"""

    # Write the script to a temporary file
    script_path = Path("_temp_agent.py")
    script_path.write_text(agent_script, encoding='utf-8')

    try:
        # Run the script as a subprocess with longer timeout
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes - Claude Code + database queries can take time
        )

        # Parse the result
        for line in result.stdout.split('\n'):
            if line.startswith('AGENT_RESULT:'):
                data = json.loads(line.replace('AGENT_RESULT:', ''))
                return data['output'], data['cost']

        # If no result found, return error info with full output
        error_msg = f"Agent execution completed but no result found.\\n\\nReturn code: {result.returncode}\\n\\nStdout (first 2000 chars):\\n{result.stdout[:2000]}\\n\\nStderr (first 2000 chars):\\n{result.stderr[:2000]}"
        return [error_msg], 0.0

    except subprocess.TimeoutExpired:
        return ["Agent timed out after 10 minutes. The query or histogram generation is taking too long."], 0.0

    finally:
        # Clean up temp file
        if script_path.exists():
            script_path.unlink()


async def run_agent(characteristic: str):
    """Async wrapper for run_agent_sync."""
    import concurrent.futures

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        output, cost = await loop.run_in_executor(pool, run_agent_sync, characteristic)
        return output, cost


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Display the home page."""
    api_key_set = bool(os.getenv('ANTHROPIC_API_KEY'))
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "api_key_set": api_key_set,
            "error": None
        }
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate_histogram(request: Request, characteristic: str = Form(...)):
    """Generate the histogram for the given characteristic."""

    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "api_key_set": False,
                "error": "ANTHROPIC_API_KEY not configured"
            }
        )

    try:
        # Run the agent
        import traceback
        import sys

        print(f"[INFO] Starting agent for characteristic: {characteristic}", file=sys.stderr)
        print(f"[INFO] This may take 2-5 minutes for database queries and analysis...", file=sys.stderr)

        agent_output, total_cost = await run_agent(characteristic)

        # Debug: Print what we got back
        print(f"[DEBUG] Agent returned {len(agent_output)} output items", file=sys.stderr)
        print(f"[DEBUG] Total cost: ${total_cost}", file=sys.stderr)
        if agent_output:
            print(f"[DEBUG] First output item (first 200 chars): {agent_output[0][:200]}", file=sys.stderr)

        # Look for the histogram file
        histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
        histogram_path = Path(histogram_filename)

        print(f"[DEBUG] Looking for histogram at: {histogram_path.absolute()}", file=sys.stderr)
        print(f"[DEBUG] File exists: {histogram_path.exists()}", file=sys.stderr)

        # Create success page
        if histogram_path.exists():
            result_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Results - Rice Database Histogram Generator</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px;
        }}
        h1 {{ color: #667eea; }}
        .success {{
            background: #efe;
            border-left: 4px solid #4f4;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            color: #363;
        }}
        img {{
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .back-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 30px;
            text-decoration: none;
            border-radius: 10px;
            margin-top: 20px;
        }}
        .cost {{
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Histogram Generated Successfully!</h1>
        <div class="success">
            <strong>Characteristic:</strong> {characteristic}<br>
            <span class="cost">💰 API Cost: ${total_cost:.4f}</span>
        </div>

        <h2>📊 Histogram</h2>
        <img src="/histogram/{histogram_filename}" alt="{characteristic} histogram">

        <a href="/" class="back-button">← Generate Another Histogram</a>
    </div>
</body>
</html>
"""
            return HTMLResponse(content=result_html)
        else:
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "api_key_set": True,
                    "error": f"Histogram file not found: {histogram_filename}"
                }
            )

    except Exception as e:
        import traceback
        import sys

        # Print full traceback to console
        print("ERROR:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "api_key_set": True,
                "error": f"{type(e).__name__}: {str(e)}\n\nCheck the console for full traceback."
            }
        )


@app.get("/histogram/{filename}")
async def get_histogram(filename: str):
    """Serve the generated histogram image."""
    file_path = Path(filename)
    if file_path.exists():
        return FileResponse(file_path)
    return {"error": "File not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
