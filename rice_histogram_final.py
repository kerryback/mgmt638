"""
Rice Database Histogram Generator - FINAL Working Version

Uses Anthropic API directly with agentic tool-calling loop.
Provides real-time streaming progress showing the agent's iterative problem-solving.

This is the PROOF OF CONCEPT that:
1. Shows how Claude agents work (iterative tool calling with error correction)
2. Includes Rice Database knowledge from rice-data-query skill
3. Streams progress in real-time to the browser
4. Works on Windows (no subprocess issues)
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import anthropic
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI(title="Rice Histogram Generator - PoC")

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
        .progress-item { background: #f9f9f9; border-left: 3px solid #667eea; padding: 10px 15px; margin: 10px 0; border-radius: 3px; font-family: monospace; font-size: 13px; white-space: pre-wrap; word-wrap: break-word; }
        .progress-item.thinking { border-left-color: #667eea; background: #f0f4ff; }
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
        <p class="subtitle">Proof of Concept - Agentic AI with Real-Time Progress</p>

        {% if not api_key_set %}
        <div class="error">
            <strong>⚠️ Configuration Error</strong><br>
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
            <button type="submit">🚀 Start Agent</button>
        </form>

        <div id="progress">
            <h3>🤖 Agent Progress</h3>
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
                    item.textContent = `💭 ${data.content}`;
                    progressLog.appendChild(item);
                    progressLog.scrollTop = progressLog.scrollHeight;
                }
                else if (data.type === 'tool') {
                    const item = document.createElement('div');
                    item.className = 'progress-item tool';
                    item.textContent = `🔧 ${data.tool_name}\n${data.content}`;
                    progressLog.appendChild(item);
                    progressLog.scrollTop = progressLog.scrollHeight;
                }
                else if (data.type === 'tool_result') {
                    const item = document.createElement('div');
                    item.className = 'progress-item result';
                    item.textContent = `✅ Result: ${data.content}`;
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
                    item.textContent = `❌ ${data.content}`;
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


async def run_agent_with_streaming(characteristic: str):
    """Run agentic loop with Anthropic API and stream progress."""

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    messages = []
    total_cost = 0.0

    prompt = f"""Create a histogram of {characteristic} across all stocks in the Rice database.

Save as '{characteristic.replace(' ', '_').lower()}_histogram.png'

Use .env to load RICE_ACCESS_TOKEN."""

    messages.append({"role": "user", "content": prompt})

    yield f"data: {json.dumps({'type': 'thinking', 'content': f'Starting agent for: {characteristic}'})}\n\n"

    for turn in range(20):  # max 20 turns
        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=[{
                "name": "bash",
                "description": "Execute a bash command",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The bash command"}
                    },
                    "required": ["command"]
                }
            }]
        )

        # Calculate cost
        cost = (response.usage.input_tokens * 3.0 / 1_000_000) + (response.usage.output_tokens * 15.0 / 1_000_000)
        total_cost += cost

        # Add assistant response
        messages.append({"role": "assistant", "content": response.content})

        # Stream thinking
        for block in response.content:
            if block.type == "text":
                preview = block.text[:300] + ('...' if len(block.text) > 300 else '')
                yield f"data: {json.dumps({'type': 'thinking', 'content': preview})}\n\n"

        # Check stop reason
        if response.stop_reason == "end_turn":
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    cmd = block.input["command"]

                    # Stream tool usage
                    cmd_preview = cmd[:200] + ('...' if len(cmd) > 200 else '')
                    yield f"data: {json.dumps({'type': 'tool', 'tool_name': 'bash', 'content': cmd_preview})}\n\n"

                    try:
                        # Run command
                        result = subprocess.run(
                            cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=120
                        )

                        output = result.stdout if result.returncode == 0 else f"Error (code {result.returncode}):\n{result.stderr}"

                        # Stream result
                        result_preview = output[:500] + ('...' if len(output) > 500 else '')
                        yield f"data: {json.dumps({'type': 'tool_result', 'content': result_preview})}\n\n"

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output[:10000]
                        })

                    except subprocess.TimeoutExpired:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Error: Command timed out after 120 seconds"
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}"
                        })

            # Add tool results to messages
            messages.append({"role": "user", "content": tool_results})

    # Check if histogram created
    histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
    if Path(histogram_filename).exists():
        yield f"data: {json.dumps({'type': 'complete', 'cost': total_cost})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'error', 'content': f'Histogram not found: {histogram_filename}'})}\n\n"


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
        run_agent_with_streaming(characteristic),
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
        <h1>✅ Success!</h1>
        <p><strong>Characteristic:</strong> {characteristic}</p>
        <p><strong>API Cost:</strong> ${cost:.4f}</p>
        <img src="/histogram/{histogram_filename}">
        <br><a href="/" class="back">← Generate Another</a>
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
    print("Rice Database Histogram Generator - Proof of Concept")
    print("="*60)
    print("\nOpen browser to: http://localhost:8005")
    print("\nThis demonstrates Claude agents:")
    print("  - Iterative problem-solving with tool calling")
    print("  - Real-time progress streaming")
    print("  - Error detection and correction")
    print("  - Rice database knowledge integration")
    print("\n" + "="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8005)
