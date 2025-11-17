"""
Simple FastAPI app using Claude Agent SDK directly (no subprocess workaround)
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, ResultMessage, TextBlock
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Fix for Windows subprocess issue - MUST be set before any asyncio operations
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

# Ensure Claude CLI is in PATH
claude_bin_path = os.path.expanduser('~/.local/bin')
if claude_bin_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{claude_bin_path};{os.environ.get('PATH', '')}"

app = FastAPI(title="Rice Database Histogram Generator")

# Create templates directory
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

# Simple HTML template
template_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Rice Histogram Generator</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
        input { width: 100%; padding: 10px; margin: 10px 0; }
        button { padding: 10px 20px; background: #4CAF50; color: white; border: none; cursor: pointer; }
        .error { background: #f44; color: white; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Rice Database Histogram Generator</h1>
    <form method="post" action="/generate">
        <label>Financial Characteristic (e.g., PE ratio, ROE, market cap):</label>
        <input type="text" name="characteristic" required>
        <button type="submit">Generate Histogram</button>
    </form>
    {% if error %}
    <div class="error">Error: {{ error }}</div>
    {% endif %}
</body>
</html>
"""

(templates_dir / "index.html").write_text(template_html, encoding='utf-8')
templates = Jinja2Templates(directory="templates")

SYSTEM_PROMPT = """You are a financial data analysis expert.

Your task:
1. Query the Rice Database for the requested financial characteristic
2. Get the MOST RECENT value for each stock
3. Create a histogram showing the distribution
4. Save as '<characteristic>_histogram.png' in the current directory

Use python-dotenv to load RICE_ACCESS_TOKEN from .env file.
"""


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "error": None})


@app.post("/generate", response_class=HTMLResponse)
async def generate(request: Request, characteristic: str = Form(...)):
    if not os.getenv('ANTHROPIC_API_KEY'):
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "ANTHROPIC_API_KEY not configured"}
        )

    try:
        print(f"[INFO] Starting agent for: {characteristic}", file=sys.stderr)

        options = ClaudeCodeOptions(
            system_prompt=SYSTEM_PROMPT,
            max_turns=10,
            allowed_tools=["Bash", "Read", "Write"],
        )

        prompt = f"""Create a histogram of {characteristic} across all stocks in the Rice database.

Save it as '{characteristic.replace(' ', '_').lower()}_histogram.png'
Use the .env file to load RICE_ACCESS_TOKEN."""

        agent_output = []
        total_cost = 0.0

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        agent_output.append(block.text)
                        print(f"[AGENT] {block.text[:100]}...", file=sys.stderr)
            elif isinstance(message, ResultMessage):
                total_cost = message.total_cost_usd
                print(f"[RESULT] Cost: ${total_cost}", file=sys.stderr)

        # Look for histogram file
        histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
        histogram_path = Path(histogram_filename)

        if histogram_path.exists():
            return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head><title>Results</title></head>
<body style="font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px;">
    <h1>Success!</h1>
    <p>Characteristic: {characteristic}</p>
    <p>Cost: ${total_cost:.4f}</p>
    <img src="/histogram/{histogram_filename}" style="max-width: 100%;">
    <p><a href="/">Generate another</a></p>
</body>
</html>
""")
        else:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error": f"Histogram not found. Agent output: {agent_output[0][:500] if agent_output else 'No output'}"}
            )

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": f"{type(e).__name__}: {str(e)}"}
        )


@app.get("/histogram/{filename}")
async def get_histogram(filename: str):
    file_path = Path(filename)
    if file_path.exists():
        return FileResponse(file_path)
    return {"error": "File not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
