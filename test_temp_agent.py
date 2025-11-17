import asyncio
import sys
import json
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, ResultMessage, TextBlock
from dotenv import load_dotenv

load_dotenv()

# Set Windows event loop policy
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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

async def main():
    print("Starting agent test...", file=sys.stderr)

    options = ClaudeCodeOptions(
        system_prompt=SYSTEM_PROMPT,
        max_turns=15,
        allowed_tools=["Bash", "Read", "Write"],
    )

    prompt = '''Please create a histogram showing the distribution of PE across all stocks in the Rice database.

Steps:
1. Determine which table(s) contain this characteristic (or the data to calculate it)
2. Query the Rice database to get the MOST RECENT value for each stock
3. Clean the data (remove nulls, extreme outliers)
4. Create a professional histogram with matplotlib
5. Include summary statistics
6. Save the plot as 'pe_histogram.png'

Remember to use the .env file to load RICE_ACCESS_TOKEN!
'''

    agent_output = []
    total_cost = 0.0

    print("Starting query...", file=sys.stderr)

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Agent: {block.text[:100]}...", file=sys.stderr)
                    agent_output.append(block.text)
        elif isinstance(message, ResultMessage):
            total_cost = message.total_cost_usd
            print(f"Result message received. Cost: ${total_cost}", file=sys.stderr)

    result = {"output": agent_output, "cost": total_cost}
    print("AGENT_RESULT:" + json.dumps(result))
    print(f"Done! Output has {len(agent_output)} items", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
