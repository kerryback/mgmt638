"""
Rice Database Histogram Generator - Using Claude Agent SDK

Uses the actual Claude Agent SDK with cli_path parameter.
Provides real-time streaming progress showing the agent's iterative problem-solving.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock, ToolUseBlock
import os
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI(title="Rice Histogram Generator - Claude Agent SDK")

# Create templates directory
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

# HTML template with SSE support for streaming progress
template_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Rice Histogram Generator - SDK</title>
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
        .progress-item { background: #f9f9f9; border-left: 3px solid #667eea; padding: 10px 15px; margin: 10px 0; border-radius: 3px; font-family: monospace; font-size: 13px; white-space: pre-wrap; word-wrap: break-word; }
        .progress-item.thinking { border-left-color: #667eea; background: #f0f4ff; }
        .progress-item.tool { border-left-color: #f39c12; background: #fef9e7; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>Rice Database Histogram Generator</h1>
        <p class="subtitle">Using Claude Agent SDK</p>

        {% if not api_key_set %}
        <div class="error">
            <strong>Configuration Error</strong><br>
            ANTHROPIC_API_KEY not found in .env file.
        </div>
        {% else %}

        <div class="info">
            <strong>How it works:</strong> Watch the AI agent iteratively solve problems:
            <ul style="margin: 10px 0 0 20px;">
                <li>Write SQL query to database</li>
                <li>Receive error message from API</li>
                <li>Debug and revise the query</li>
                <li>Generate histogram with statistics</li>
            </ul>
        </div>

        <form id="histogramForm">
            <label><strong>Financial Characteristic:</strong></label>
            <input type="text" id="characteristic" placeholder="e.g., PE ratio, market cap, ROE..." required>
            <button type="submit">Start Agent</button>
        </form>

        <div id="progress">
            <h3>Agent Progress</h3>
            <div class="spinner"></div>
            <div id="progressLog"></div>
        </div>

        {% endif %}
    </div>

    <script>
        document.getElementById('histogramForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const characteristic = document.getElementById('characteristic').value;
            const progress = document.getElementById('progress');
            const progressLog = document.getElementById('progressLog');

            progress.classList.add('active');
            progressLog.innerHTML = '';

            const eventSource = new EventSource(`/generate_stream?characteristic=${encodeURIComponent(characteristic)}`);

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'thinking') {
                    const item = document.createElement('div');
                    item.className = 'progress-item thinking';
                    item.textContent = `Agent: ${data.content}`;
                    progressLog.appendChild(item);
                    progressLog.scrollTop = progressLog.scrollHeight;
                }
                else if (data.type === 'tool') {
                    const item = document.createElement('div');
                    item.className = 'progress-item tool';
                    item.textContent = `Tool: ${data.tool_name}\n${data.content}`;
                    progressLog.appendChild(item);
                    progressLog.scrollTop = progressLog.scrollHeight;
                }
                else if (data.type === 'complete') {
                    eventSource.close();
                    window.location.href = `/result?characteristic=${encodeURIComponent(characteristic)}&cost=${data.cost}`;
                }
                else if (data.type === 'error') {
                    const item = document.createElement('div');
                    item.className = 'progress-item error';
                    item.textContent = `Error: ${data.content}`;
                    progressLog.appendChild(item);
                    eventSource.close();
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                const item = document.createElement('div');
                item.className = 'progress-item error';
                item.textContent = 'Connection lost';
                progressLog.appendChild(item);
            };
        });
    </script>
</body>
</html>
"""

(templates_dir / "index.html").write_text(template_html, encoding='utf-8')
templates = Jinja2Templates(directory="templates")

# System prompt incorporating rice-data-query skill knowledge
SYSTEM_PROMPT = """You are a financial data analysis expert specializing in the Rice Data Portal.

TASK: Create a histogram showing the distribution of a financial characteristic across all stocks.

RICE DATABASE INFORMATION (from rice-data-query skill):

API: https://data-portal.rice-business.org/api/query
Authentication: RICE_ACCESS_TOKEN from .env (use python-dotenv)

Request format:
```python
import requests
from dotenv import load_dotenv
import os

load_dotenv()
response = requests.post(
    "https://data-portal.rice-business.org/api/query",
    headers={"Authorization": f"Bearer {os.getenv('RICE_ACCESS_TOKEN')}", "Content-Type": "application/json"},
    json={"query": "YOUR SQL HERE"},
    timeout=30
)
data = response.json()
df = pd.DataFrame(data['data'])[data['columns']]
```

CRITICAL TABLES:
- DAILY: pe, pb, ps, marketcap (in thousands!), ev, evebit, evebitda
- SEP: prices (close, closeadj, open, high, low, volume)
- SF1: fundamentals (equity, revenue, netinc, assets, debt, roe, roa, etc.)
  - Use dimension = 'ARY' for annual or 'ARQ' for quarterly
- TICKERS: ticker, name, sector, industry, exchange

CRITICAL RULES:
1. All date columns are VARCHAR - MUST cast: date::DATE
2. For most recent: WHERE date = (SELECT MAX(date) FROM table_name)
3. SF1 most recent: WHERE dimension = 'ARY' AND reportperiod = (SELECT MAX(reportperiod) FROM sf1 WHERE dimension = 'ARY')
4. Filter NULL and extreme outliers (e.g., PE > 1000 or PE < 0)
5. Use matplotlib with clear labels, title, and summary statistics

Be concise. Write script, run it, debug if needed, verify histogram created."""


async def run_agent_with_sdk(characteristic: str):
    """Run Claude Agent SDK with streaming progress."""

    options = ClaudeAgentOptions(
        cli_path=r"C:\Users\kerry\.local\bin\claude.exe",
        system_prompt=SYSTEM_PROMPT,
        max_turns=20,
        allowed_tools=["Bash", "Read", "Write"]
    )

    prompt = f"""Create a histogram of {characteristic} across all stocks in the Rice database.

Save as '{characteristic.replace(' ', '_').lower()}_histogram.png'

Use .env to load RICE_ACCESS_TOKEN."""

    yield f"data: {json.dumps({'type': 'thinking', 'content': f'Starting agent for: {characteristic}'})}\n\n"

    total_cost = 0.0

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # Stream agent's thinking
                        preview = block.text[:300] + ('...' if len(block.text) > 300 else '')
                        yield f"data: {json.dumps({'type': 'thinking', 'content': preview})}\n\n"

                    elif isinstance(block, ToolUseBlock):
                        # Stream tool usage
                        tool_name = block.name
                        if tool_name == "Bash":
                            cmd_preview = str(block.input.get('command', ''))[:200]
                            yield f"data: {json.dumps({'type': 'tool', 'tool_name': 'Bash', 'content': cmd_preview})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'tool', 'tool_name': tool_name, 'content': str(block.input)[:200]})}\n\n"

            elif isinstance(message, ResultMessage):
                total_cost = message.total_cost_usd

        # Check if histogram was created
        histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
        if Path(histogram_filename).exists():
            yield f"data: {json.dumps({'type': 'complete', 'cost': total_cost})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Histogram not found: {histogram_filename}'})}\n\n"

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"ERROR: {error_msg}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "api_key_set": bool(os.getenv('ANTHROPIC_API_KEY'))
    })


@app.get("/generate_stream")
async def generate_stream(characteristic: str):
    """Server-Sent Events endpoint."""
    return StreamingResponse(
        run_agent_with_sdk(characteristic),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@app.get("/result", response_class=HTMLResponse)
async def result(characteristic: str, cost: float):
    """Display histogram result."""
    histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"

    if Path(histogram_filename).exists():
        return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head><title>Results - {characteristic}</title>
<style>
    body {{ font-family: Arial; max-width: 1000px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
    .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    h1 {{ color: #333; }}
    img {{ max-width: 100%; border-radius: 5px; margin: 20px 0; }}
    .back {{ display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
</style>
</head>
<body>
    <div class="container">
        <h1>Success!</h1>
        <p><strong>Characteristic:</strong> {characteristic}</p>
        <p><strong>API Cost:</strong> ${cost:.4f}</p>
        <img src="/histogram/{histogram_filename}">
        <br><a href="/" class="back">Generate Another</a>
    </div>
</body>
</html>
""")
    else:
        return HTMLResponse(f"<h1>Error: Histogram not found</h1><a href='/'>Go back</a>")


@app.get("/histogram/{filename}")
async def get_histogram(filename: str):
    if Path(filename).exists():
        return FileResponse(filename)
    return {"error": "Not found"}


if __name__ == "__main__":
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("ERROR: ANTHROPIC_API_KEY not found")
        exit(1)

    import uvicorn
    print("\n" + "="*60)
    print("Rice Database Histogram Generator")
    print("Using Claude Agent SDK")
    print("="*60)
    print("\nOpen browser to: http://localhost:8006")
    print("\n" + "="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8006)
