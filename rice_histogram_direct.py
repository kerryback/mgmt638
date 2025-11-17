"""
Rice Database Histogram Generator - Direct Anthropic API

Uses Anthropic API directly instead of Claude Agent SDK to avoid Windows subprocess issues.
Implements a simple agentic loop with tool calling.
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import anthropic
import os
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

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
        body { font-family: Arial; max-width: 1000px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 30px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #ddd; border-radius: 5px; font-size: 16px; }
        button { padding: 12px 30px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        button:hover { background: #45a049; }
        .error { background: #fee; border-left: 4px solid #f44; padding: 15px; margin: 20px 0; border-radius: 5px; color: #c33; }
        .info { background: #e3f2fd; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0; border-radius: 5px; }
        .result-img { max-width: 100%; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .cost { color: #666; font-size: 14px; margin-top: 10px; }
        .loading { color: #666; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Rice Database Histogram Generator</h1>

        {% if not api_key_set %}
        <div class="error">
            <strong>⚠️ Configuration Error</strong><br>
            ANTHROPIC_API_KEY not found in .env file.
        </div>
        {% else %}

        <div class="info">
            <strong>How it works:</strong> Enter a financial characteristic (e.g., "PE ratio", "ROE", "market cap")
            and the AI will query the Rice database and create a histogram.
            <br><br>
            <strong>Note:</strong> This may take 2-5 minutes for database queries and analysis.
        </div>

        <form method="post" action="/generate">
            <label><strong>Financial Characteristic:</strong></label>
            <input type="text" name="characteristic" placeholder="e.g., PE ratio, ROE, market cap..." required>
            <button type="submit">🚀 Generate Histogram</button>
        </form>

        {% if error %}
        <div class="error">
            <strong>Error:</strong> {{ error }}
        </div>
        {% endif %}

        {% endif %}
    </div>
</body>
</html>
"""

(templates_dir / "index.html").write_text(template_html, encoding='utf-8')
templates = Jinja2Templates(directory="templates")


SYSTEM_PROMPT = """You are a financial data analysis expert. Your task is to create a histogram of a financial characteristic across stocks in the Rice database.

You have access to Python tools via bash commands. Follow these steps:

1. Write a Python script that:
   - Loads RICE_ACCESS_TOKEN from .env using python-dotenv
   - Queries the Rice database for the requested characteristic
   - Gets the MOST RECENT value for each stock
   - Cleans the data (removes nulls and extreme outliers)
   - Creates a professional histogram with matplotlib
   - Includes summary statistics (mean, median, std)
   - Saves as '{characteristic}_histogram.png'

2. Run the script using python command

Rice Database info:
- Use DuckDB SQL via httpx POST to https://data-portal.rice-business.org/api/query
- Tables: daily (prices), sf1 (fundamentals), sep (financial ratios), metrics (valuation)
- All dates are VARCHAR - cast to DATE for comparisons
- For most recent data: WHERE date = (SELECT MAX(date) FROM table_name)

Available tools:
- bash: Run shell commands (python scripts, etc.)

**IMPORTANT for Windows compatibility:**
- DO NOT use heredoc syntax (cat > file << 'EOF')
- Instead, use Python directly: python -c "open('file.py', 'w').write('script content')"
- OR write script inline: python -c "import os; [your code here]"

Be concise. Write the script, run it, verify the histogram was created."""


def run_agent_loop(characteristic: str, max_turns: int = 20):
    """Run a simple agentic loop using Anthropic API directly."""

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    messages = []
    total_cost = 0.0

    # Initial prompt
    user_prompt = f"""Create a histogram showing the distribution of {characteristic} across all stocks in the Rice database.

Save the plot as '{characteristic.replace(' ', '_').lower()}_histogram.png'

Use the .env file to load RICE_ACCESS_TOKEN."""

    messages.append({
        "role": "user",
        "content": user_prompt
    })

    for turn in range(max_turns):
        print(f"\n=== Turn {turn + 1} ===")

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=[
                {
                    "name": "bash",
                    "description": "Execute a bash command. Use this to run Python scripts or other shell commands.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The bash command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            ]
        )

        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)
        total_cost += cost

        print(f"Tokens: {input_tokens} in, {output_tokens} out | Cost: ${cost:.4f}")

        # Add assistant response to messages
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        # Check stop reason
        if response.stop_reason == "end_turn":
            print("Agent finished")
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"\nTool: {tool_name}")
                    print(f"Input: {tool_input}")

                    if tool_name == "bash":
                        command = tool_input["command"]
                        print(f"Running: {command[:200]}")

                        try:
                            # Windows fix: Use Python to write files instead of cat/heredoc
                            if "cat >" in command and "<<" in command:
                                print("Detected heredoc - converting to Python file write")
                                command = "python -c \"import sys; content = '''%CONTENT%'''; open('%FILE%', 'w').write(content); print('File created successfully')\""
                                # Extract filename and content
                                # For now, skip heredoc commands and suggest direct Python write
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": "Error: Heredoc syntax not supported on Windows. Please write the Python script directly using Python's open() function or use a simple command."
                                })
                                continue

                            result = subprocess.run(
                                command,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=120
                            )

                            output = result.stdout if result.returncode == 0 else f"Error (code {result.returncode}):\n{result.stderr}"
                            print(f"Output: {output[:500]}")

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output[:10000]  # Limit output size
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
            messages.append({
                "role": "user",
                "content": tool_results
            })
        else:
            print(f"Unexpected stop reason: {response.stop_reason}")
            break

    return total_cost


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


@app.post("/generate", response_class=HTMLResponse)
async def generate(request: Request, characteristic: str = Form(...)):
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
        print(f"\n=== Starting histogram generation for: {characteristic} ===")

        # Run the agent loop
        total_cost = run_agent_loop(characteristic, max_turns=20)

        # Look for histogram file
        histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
        histogram_path = Path(histogram_filename)

        print(f"\nLooking for: {histogram_path.absolute()}")
        print(f"Exists: {histogram_path.exists()}")

        if histogram_path.exists():
            result_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Results</title>
    <style>
        body {{ font-family: Arial; max-width: 1000px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        img {{ max-width: 100%; border-radius: 5px; margin: 20px 0; }}
        .back {{ display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
        .cost {{ color: #666; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Success!</h1>
        <p><strong>Characteristic:</strong> {characteristic}</p>
        <p class="cost"><strong>API Cost:</strong> ${total_cost:.4f}</p>
        <img src="/histogram/{histogram_filename}" alt="Histogram">
        <br>
        <a href="/" class="back">← Generate Another</a>
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
                    "error": f"Histogram file not found: {histogram_filename}. Check console for details."
                }
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "api_key_set": True,
                "error": f"{type(e).__name__}: {str(e)}"
            }
        )


@app.get("/histogram/{filename}")
async def get_histogram(filename: str):
    file_path = Path(filename)
    if file_path.exists():
        return FileResponse(file_path)
    return {"error": "File not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
