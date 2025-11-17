"""
Rice Database Characteristic Histogram Agent - Streamlit Web App

This Streamlit app uses the Claude Agent SDK to:
1. Accept a user-specified financial characteristic
2. Query the Rice Database to get the most recent value for each stock
3. Calculate the characteristic if needed (e.g., financial ratios)
4. Display a histogram of the characteristic values

Usage:
    streamlit run rice_characteristic_histogram.py
"""

import streamlit as st
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure Claude CLI is in PATH
claude_bin_path = os.path.expanduser('~/.local/bin')
if claude_bin_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{claude_bin_path};{os.environ.get('PATH', '')}"


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

AVAILABLE RICE DATABASE TABLES:

- TICKERS: Company information (sector, industry, exchange, etc.)
- SEP: Daily stock prices (close, closeadj, volume, etc.)
- DAILY: Daily valuation metrics (pe, pb, ps, marketcap, ev, evebit, evebitda)
- SF1: Fundamental data from 10-K/10-Q (balance sheet, income statement, cash flow, ratios)
- METRICS: Moving averages and technical indicators

COMMON CHARACTERISTICS AND WHERE TO FIND THEM:

- PE ratio: DAILY table (pe column) - use most recent date
- Market cap: DAILY table (marketcap column in thousands) - use most recent date
- ROE, ROA, ROIC: SF1 table - use most recent reportperiod per ticker, dimension='ARY'
- Current ratio, Quick ratio: SF1 table - use most recent reportperiod per ticker
- Debt-to-equity: SF1 table (de column) - use most recent reportperiod per ticker
- Revenue, Net Income, Assets: SF1 table - use most recent reportperiod per ticker
- Calculated ratios: Get components from SF1 and calculate in pandas

HISTOGRAM BEST PRACTICES:

1. Remove extreme outliers (e.g., values beyond 99th percentile for ratios)
2. Remove negative values for ratios that should be positive
3. Use 30-50 bins for good granularity
4. Add vertical lines for mean and median
5. Include summary statistics in the title or as text on the plot
6. Save the plot as a PNG file with a descriptive name

Remember: The user will provide the characteristic name. You need to figure out how to get it!
"""


async def run_agent(characteristic: str):
    """Run the agent to create a histogram for the given characteristic."""

    # Configure the agent options
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        max_turns=15,  # Allow multiple turns for complex queries
        allowed_tools=["Bash", "Read", "Write"],  # Allow file operations and code execution
    )

    # Create the prompt for the agent
    prompt = f"""Please create a histogram showing the distribution of {characteristic} across all stocks in the Rice database.

Steps:
1. Determine which table(s) contain this characteristic (or the data to calculate it)
2. Query the Rice database to get the MOST RECENT value for each stock
3. Clean the data (remove nulls, extreme outliers)
4. Create a professional histogram with matplotlib
5. Include summary statistics
6. Save the plot as '{characteristic.replace(' ', '_').lower()}_histogram.png'

Remember to use the .env file to load RICE_ACCESS_TOKEN!
"""

    # Run the agent and collect responses
    agent_output = []
    total_cost = 0.0

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            # Collect agent's text responses
            for block in message.content:
                if isinstance(block, TextBlock):
                    agent_output.append(block.text)

        elif isinstance(message, ResultMessage):
            # Track costs
            total_cost = message.total_cost_usd

    return agent_output, total_cost


def main():
    """Main Streamlit app."""

    st.set_page_config(
        page_title="Rice Database Histogram Generator",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 Rice Database Characteristic Histogram Generator")
    st.markdown("---")

    # Check for ANTHROPIC_API_KEY
    if not os.getenv('ANTHROPIC_API_KEY'):
        st.error("⚠️ ANTHROPIC_API_KEY not found!")
        st.markdown("""
        Please add your Anthropic API key to the `.env` file:

        ```
        ANTHROPIC_API_KEY=your_api_key_here
        RICE_ACCESS_TOKEN=your_rice_token_here
        ```

        You can get your Anthropic API key from: https://console.anthropic.com/
        """)
        st.stop()

    # Check for RICE_ACCESS_TOKEN
    if not os.getenv('RICE_ACCESS_TOKEN'):
        st.warning("⚠️ RICE_ACCESS_TOKEN not found in .env file!")
        st.markdown("""
        The agent will need access to the Rice Data Portal. Please add your token to the `.env` file:

        ```
        RICE_ACCESS_TOKEN=your_rice_token_here
        ```

        You can get your token from: https://data-portal.rice-business.org
        """)

    # Sidebar with information
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This app uses Claude Agent SDK to create histograms of financial characteristics
        from the Rice Data Portal.
        """)

        st.header("📝 Example Characteristics")
        st.markdown("""
        - PE ratio
        - Market capitalization
        - Return on Equity (ROE)
        - Debt-to-equity ratio
        - Current ratio
        - Revenue
        - Book-to-market ratio
        - Price-to-sales ratio
        - Gross margin
        - Operating margin
        """)

        st.header("🔑 Requirements")
        st.markdown("""
        Make sure you have:
        - `.env` file with `RICE_ACCESS_TOKEN`
        - Claude Agent SDK installed
        - Internet connection
        """)

    # Main content
    st.markdown("""
    ### Enter a Financial Characteristic

    The AI agent will automatically:
    1. Determine which database tables to query
    2. Retrieve the most recent data for each stock
    3. Calculate ratios if needed
    4. Create a professional histogram with statistics
    """)

    # Input field for characteristic
    characteristic = st.text_input(
        "What characteristic would you like to visualize?",
        placeholder="e.g., PE ratio, ROE, market cap...",
        help="Enter any financial characteristic. The agent will figure out how to get it!"
    )

    # Generate button
    if st.button("🚀 Generate Histogram", type="primary", disabled=not characteristic):
        if not characteristic.strip():
            st.error("Please enter a characteristic name.")
            return

        # Create a progress container
        with st.spinner(f"🤖 Agent is working on '{characteristic}'... This may take a moment."):
            progress_placeholder = st.empty()
            output_placeholder = st.empty()

            try:
                # Run the agent
                progress_placeholder.info("Agent is querying the database and creating the histogram...")

                # Use asyncio with proper event loop handling for Streamlit
                import nest_asyncio
                nest_asyncio.apply()

                agent_output, total_cost = asyncio.run(run_agent(characteristic))

                # Display agent output
                progress_placeholder.success("✅ Agent completed successfully!")

                st.markdown("---")
                st.subheader("🤖 Agent Output")

                # Display each output block
                for output in agent_output:
                    with st.expander("View Agent Response", expanded=True):
                        st.text(output)

                # Try to find and display the generated histogram
                st.markdown("---")
                st.subheader("📊 Generated Histogram")

                # Look for the histogram file
                histogram_filename = f"{characteristic.replace(' ', '_').lower()}_histogram.png"
                histogram_path = Path(histogram_filename)

                if histogram_path.exists():
                    st.image(str(histogram_path), use_container_width=True)

                    # Provide download button
                    with open(histogram_path, "rb") as file:
                        st.download_button(
                            label="💾 Download Histogram",
                            data=file,
                            file_name=histogram_filename,
                            mime="image/png"
                        )
                else:
                    st.warning(f"Histogram file not found: {histogram_filename}")
                    st.info("The agent may have saved it with a different name. Check the output above.")

                # Display cost
                st.markdown("---")
                st.metric("💰 API Cost", f"${total_cost:.4f}")

            except Exception as e:
                progress_placeholder.error(f"❌ Error: {str(e)}")
                st.exception(e)


if __name__ == "__main__":
    main()
