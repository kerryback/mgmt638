"""
Rice Database Histogram Generator - Proof of Concept

Uses Claude Agent SDK with streaming progress feedback.
Demonstrates agentic problem-solving with real-time visibility.
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, ResultMessage, TextBlock, ToolUseBlock
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import json

# Windows event loop fix - MUST be before any asyncio operations
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

app = FastAPI(title="Rice Histogram Generator - Proof of Concept")

# Create templates directory
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

# HTML template with SSE support for streaming progress
template_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Rice Histogram Generator - PoC</title>
    <style>
        body { font-family: Arial; max-width: 1000px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 10px; }
        .subtitle { color: #666; font-size: 14px; margin-bottom: 30px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #ddd; border-radius: 5px; font-size: 16px; box-sizing: border-box; }
        button { padding: 12px 30px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        button:hover { background: #5568d3; }
        .error { background: #fee; border-left: 4px solid #f44; padding: 15px; margin: 20px 0; border-radius: 5px; color: #c33; }
        .info { background: #e3f2fd; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0; border-radius: 5px; }
        #progress { display: none; margin: 20px 0; }
        #progress.active { display: block; }
        .progress-item { background: #f9f9f9; border-left: 3px solid #667eea; padding: 10px 15px; margin: 10px 0; border-radius: 3px; font-family: monospace; font-size: 13px; }
        .progress-item.tool { border-left-color: #f39c12; background: #fef9e7; }
        .progress-item.result { border-left-color: #27ae60; background: #e8f8f5; }
        .progress-item.error { border-left-color: #e74c3c; background: #fadbd8; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Rice Database Histogram Generator</h1>
        <p class="subtitle">Proof of Concept - Claude Agent SDK with Real-Time Progress</p>

        {% if not api_key_set %}
        <div class="error">
            <strong>⚠️ Configuration Error</strong><br>
            ANTHROPIC_API_KEY not found in .env file.
        </div>
        {% else %}

        <div class="info">
            <strong>How it works:</strong> Enter a financial characteristic and watch the AI agent:
            <ul style="margin: 10px 0 0 20px;">
                <li>Determine which database tables to query</li>
                <li>Write and execute SQL queries</li>
                <li>Debug errors and retry with corrected code</li>
                <li>Create a professional histogram with statistics</li>
            </ul>
        </div>

        <form id="histogramForm">
            <label><strong>Financial Characteristic:</strong></label>
            <input type="text" id="characteristic" name="characteristic" placeholder="e.g., PE ratio, market cap, ROE..." required>
            <button type="submit">🚀 Generate Histogram</button>
        </form>

        <div id="progress">
            <h3>🤖 Agent Progress</h3>
            <div class="spinner"></div>
            <div id="progressLog"></div>
        </div>

        {% if error %}
        <div class="error">
            <strong>Error:</strong> {{ error }}
        </div>
        {% endif %}

        {% endif %}
    </div>

    <script>
        document.getElementById('histogramForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const characteristic = document.getElementById('characteristic').value;
            const progress = document.getElementById('progress');
            const progressLog = document.getElementById('progressLog');

            // Show progress section
            progress.classList.add('active');
            progressLog.innerHTML = '';

            // Connect to SSE endpoint for streaming progress
            const eventSource = new EventSource(`/generate_stream?characteristic=${encodeURIComponent(characteristic)}`);

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'message') {
                    const item = document.createElement('div');
                    item.className = 'progress-item';
                    item.textContent = `💬 ${data.content}`;
                    progressLog.appendChild(item);
                    progressLog.scrollTop = progressLog.scrollHeight;
                }
                else if (data.type === 'tool') {
                    const item = document.createElement('div');
                    item.className = 'progress-item tool';
                    item.innerHTML = `🔧 <strong>${data.tool}</strong>: ${data.content}`;
                    progressLog.appendChild(item);
                    progressLog.scrollTop = progressLog.scrollHeight;
                }
                else if (data.type === 'complete') {
                    eventSource.close();
                    // Redirect to result page
                    window.location.href = `/result?characteristic=${encodeURIComponent(characteristic)}&cost=${data.cost}`;
                }
                else if (data.type === 'error') {
                    const item = document.createElement('div');
                    item.className = 'progress-item error';
                    item.textContent = `❌ Error: ${data.content}`;
                    progressLog.appendChild(item);
                    eventSource.close();
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                const item = document.createElement('div');
                item.className = 'progress-item error';
                item.textContent = '❌ Connection lost';
                progressLog.appendChild(item);
            };
        });
    </script>
</body>
</html>
"""

(templates_dir / "index.html").write_text(template_html, encoding='utf-8')
templates = Jinja2Templates(directory="templates")

# System prompt with rice-data-query skill information
SYSTEM_PROMPT = """You are a financial data analysis expert specializing in the Rice Data Portal.

Your task:
1. Query the Rice Database for the requested financial characteristic
2. Get the MOST RECENT value for each stock
3. Clean the data (remove nulls and extreme outliers)
4. Create a histogram showing the distribution
5. Save as '<characteristic>_histogram.png'

CRITICAL RICE DATABASE INFORMATION:

API Endpoint: https://data-portal.rice-business.org/api/query
Authentication: Use RICE_ACCESS_TOKEN from .env file (load with python-dotenv)

Request format:
```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')

response = requests.post(
    "https://data-portal.rice-business.org/api/query",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
    json={"query": "YOUR SQL HERE"},
    timeout=30
)
data = response.json()
```

KEY TABLES AND COLUMNS:

1. DAILY table (valuation metrics):
   - Columns: ticker, date, pe, pb, ps, marketcap, ev, evebit, evebitda
   - For PE ratio: SELECT ticker, date, pe FROM daily WHERE date = (SELECT MAX(date) FROM daily)

2. SEP table (prices):
   - Columns: ticker, date, close, closeadj, open, high, low, volume
   - Get most recent: WHERE date = (SELECT MAX(date) FROM sep)

3. SF1 table (fundamentals):
   - Columns: ticker, reportperiod, dimension, equity, revenue, netinc, assets, debt, roe, roa, etc.
   - CRITICAL: Use dimension = 'ARY' for annual or 'ARQ' for quarterly
   - Most recent: WHERE dimension = 'ARY' AND reportperiod = (SELECT MAX(reportperiod) FROM sf1 WHERE dimension = 'ARY')

4. TICKERS table (company info):
   - Columns: ticker, name, sector, industry, exchange

CRITICAL RULES:
- All date columns are VARCHAR - MUST cast to DATE for comparisons: date::DATE
- Filter out NULL values and extreme outliers (e.g., PE > 1000 or PE < 0)
- Use matplotlib for histogram with clear labels and title
- Include summary statistics (mean, median, count)
- ALWAYS use python-dotenv to load RICE_ACCESS_TOKEN

Be concise. Write the code, run it, debug if needed, verify the histogram was created."""


async def generate_histogram_stream(characteristic: str):
    """Stream agent progress using Server-Sent Events."""

    try:
        # Configure agent
        options = ClaudeCodeOptions(
            system_prompt=SYSTEM_PROMPT,
            max_turns=20,
            allowed_tools=["Bash", "Read", "Write"]
        )

        prompt = f"""Create a histogram showing the distribution of {characteristic} across all stocks in the Rice database.

Save the plot as '{characteristic.replace(' ', '_').lower()}_histogram.png'

Use the .env file to load RICE_ACCESS_TOKEN."""

        total_cost = 0.0

        yield f"data: {json.dumps({'type': 'message', 'content': f'Starting agent for: {characteristic}'})}\n\n"

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # Send agent's thinking
                        text_preview = block.text[:200] + ('...' if len(block.text) > 200 else '')
                        yield f"data: {json.dumps({'type': 'message', 'content': text_preview})}\n\n"

                    elif isinstance(block, ToolUseBlock):
                        # Send tool usage
                        tool_name = block.name
                        if tool_name == "Bash":
                            cmd_preview = str(block.input.get('command', ''))[:150]
                            yield f"data: {json.dumps({'type': 'tool', 'tool': 'Bash', 'content': cmd_preview})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'tool', 'tool': tool_name, 'content': str(block.input)[:150]})}\n\n"

            elif isinstance(message, ResultMessage):
                total_cost = message.total_cost_usd
                yield f"data: {json.dumps({'type': 'message', 'content': f'Agent completed. Total cost: ${total_cost:.4f}'})}\n\n"

        # Check if histogram was created
        histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
        histogram_path = Path(histogram_filename)

        if histogram_path.exists():
            yield f"data: {json.dumps({'type': 'complete', 'cost': total_cost})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Histogram file not found: {histogram_filename}'})}\n\n"

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    api_key_set = bool(os.getenv('ANTHROPIC_API_KEY'))
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "api_key_set": api_key_set,
            "error": None
        }
    )


@app.get("/generate_stream")
async def generate_stream(characteristic: str):
    """Server-Sent Events endpoint for streaming progress."""
    return StreamingResponse(
        generate_histogram_stream(characteristic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/result", response_class=HTMLResponse)
async def result(characteristic: str, cost: float):
    """Display the generated histogram."""
    histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
    histogram_path = Path(histogram_filename)

    if histogram_path.exists():
        return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
    <title>Results - {characteristic}</title>
    <style>
        body {{ font-family: Arial; max-width: 1000px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        img {{ max-width: 100%; border-radius: 5px; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .back {{ display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
        .cost {{ color: #666; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Success!</h1>
        <p><strong>Characteristic:</strong> {characteristic}</p>
        <p class="cost"><strong>API Cost:</strong> ${cost:.4f}</p>
        <img src="/histogram/{histogram_filename}" alt="Histogram">
        <br>
        <a href="/" class="back">← Generate Another</a>
    </div>
</body>
</html>
""")
    else:
        return HTMLResponse(f"<h1>Error: Histogram not found</h1><p>{histogram_filename}</p><a href='/'>Go back</a>")


@app.get("/histogram/{filename}")
async def get_histogram(filename: str):
    file_path = Path(filename)
    if file_path.exists():
        return FileResponse(file_path)
    return {"error": "File not found"}


if __name__ == "__main__":
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("ERROR: ANTHROPIC_API_KEY not found in .env file")
        sys.exit(1)

    import uvicorn
    print("\n" + "="*60)
    print("Rice Database Histogram Generator - Proof of Concept")
    print("="*60)
    print("\nOpen your browser to: http://localhost:8004")
    print("\nFeatures:")
    print("   - Uses Claude Agent SDK directly (no workarounds)")
    print("   - Real-time progress streaming")
    print("   - Shows agent's iterative problem-solving")
    print("\n" + "="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8004)
