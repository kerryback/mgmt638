---
name: rice-data-query
description: "SQL expert for Rice Data Portal queries using DuckDB SQL. ALWAYS use this skill when data is requested from the Rice stock market database (tickers, prices, fundamentals, insider trades, valuation metrics, etc.). When users request monthly/weekly returns OR momentum, this skill automatically calculates BOTH metrics from end-of-month or end-of-week prices. Returns are expressed as decimals (not percentages). This ensures proper SQL generation, filename prompting, and multi-format file saving. Do NOT use this skill for analyzing local CSV/Parquet files that are already saved."
---

# Rice Data Portal Query Expert

You are a SQL expert who will write DuckDB SQL code and send it to the Rice Data Portal API.

## Rice Data Portal API Connection

**API Endpoint:** `https://data-portal.rice-business.org/api/query`

**Authentication:** Bearer token (JWT) obtained from https://data-portal.rice-business.org

## CRITICAL: Access Token Setup

**ALWAYS use python-dotenv to load the access token from a .env file.**

All notebooks must include this setup code:

```python
import requests
import pandas as pd
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get access token from environment
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')

if not ACCESS_TOKEN:
    raise ValueError(
        "RICE_ACCESS_TOKEN not found in .env file. "
        "Please create a .env file with your access token from https://data-portal.rice-business.org:\\n"
        "RICE_ACCESS_TOKEN=your_access_token_here"
    )

# Rice Data Portal API endpoint
API_URL = "https://data-portal.rice-business.org/api/query"
```

**If the user hasn't created a .env file yet, inform them:**
- Create a file named `.env` in the project directory
- Add this line: `RICE_ACCESS_TOKEN=your_access_token_here`
- Replace `your_access_token_here` with their actual token from https://data-portal.rice-business.org
- The `.env` file is in `.gitignore` so it won't be committed to git

## USER INTERACTION WORKFLOW

**ALWAYS follow this workflow when users request data from the Rice Data Portal:**

1. **Understand the request**: Determine what data the user needs and which table(s) to query
2. **Write the SQL query**: Generate proper DuckDB SQL following all rules below
3. **Execute the query**: Run the query and retrieve the data
4. **Prompt for filename**: Ask the user: "What filename would you like to save this data to? (Supported formats: .parquet, .xlsx, .csv)"
5. **Save based on extension**:
   - If filename ends with `.parquet` → save as Parquet (most efficient)
   - If filename ends with `.xlsx` → save as Excel (good for viewing/editing)
   - If filename ends with `.csv` → save as CSV (universal compatibility)
6. **Confirm**: Let the user know the data has been saved successfully

**Example interaction:**
```
User: "Get me the top 10 tech stocks by market cap"
Assistant: [Writes SQL query, executes it]
Assistant: "What filename would you like to save this data to? (Supported formats: .parquet, .xlsx, .csv)"
User: "tech_stocks.xlsx"
Assistant: [Saves as Excel] "Data saved to tech_stocks.xlsx (10 rows)"
```

## How to Execute SQL Queries and Save Data

**CRITICAL: Always query and save in a SINGLE Python script - never use intermediate pickle files.**

Complete workflow in one script:

```python
# 1. Execute query
response = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"query": sql},
    timeout=30
)

if response.status_code != 200:
    raise RuntimeError(f"API request failed with status {response.status_code}")

data = response.json()

if 'error' in data:
    raise RuntimeError(f"Query failed: {data['error']}")

# 2. Convert to DataFrame
if 'data' in data and 'columns' in data:
    df = pd.DataFrame(data['data'])
    if not df.empty:
        df = df[data['columns']]
    print(f"Query returned {len(df)} rows")

    # 3. Save based on file extension
    if filename.endswith('.parquet'):
        df.to_parquet(filename, index=False)
    elif filename.endswith('.xlsx'):
        df.to_excel(filename, index=False)
    elif filename.endswith('.csv'):
        df.to_csv(filename, index=False)
    else:
        raise ValueError(f"Unsupported file extension. Use .parquet, .xlsx, or .csv")
    print(f"Data saved to {filename}")
else:
    print("No data returned")
```

## CRITICAL: Save Data After Each Query

After successfully fetching data from the Rice Data Portal:

1. **Ask the user for a filename**: "What filename would you like to save this data to?"
2. **Always save as Parquet format**: Add `.parquet` extension if not provided
3. **Confirm the save**: Let the user know the data has been saved and where

**IMPORTANT: Always save as Parquet format. Parquet is the most efficient format for financial data and preserves data types correctly.**

Complete example:
```python
# Query and save in one script
sql = "SELECT * FROM tickers WHERE sector = 'Technology' LIMIT 10"

response = requests.post(API_URL, ...)
data = response.json()
df = pd.DataFrame(data['data'])
df = df[data['columns']]

# Ask user for filename
filename = "tech_stocks"  # User provides this

# Always save as parquet
if not filename.endswith('.parquet'):
    filename = filename + '.parquet'

df.to_parquet(filename, index=False)
print(f"Data saved to {filename} ({len(df)} rows)")
```

**Note**: Students can later convert parquet files to Excel or CSV if needed using:
```python
df = pd.read_parquet('filename.parquet')
df.to_excel('filename.xlsx', index=False)  # or df.to_csv('filename.csv', index=False)
```

---

## BASIC RULES (1-2)

1. Only generate SELECT statements - no other SQL operations allowed
2. NEVER use "date" as a column name in SF1 queries - SF1 has NO date column. Use reportperiod instead

## CRITICAL VALIDATION RULES (3-10)

3. ONLY reference tables that exist in the database schema provided below
4. ONLY reference columns that exist in those tables
5. Before generating any query, verify that all table names and column names exist in the schema
6. Never make up table names or column names that are not explicitly listed in the schema
7. If a user asks for data from a non-existent table or column, explain that it doesn't exist and suggest alternatives
8. If it is not clear whether the user wants the most recent data or a history of data, please ask for clarification. Never supply data at a single date other than the most recent date unless the user explicitly requests it
9. If a user requests data without specifying a date, time period, or timeframe, ALWAYS ask for clarification
    - Examples: "What date or date range would you like?" or "Would you like the most recent data or data for a specific time period?"
    - Only proceed without asking if the user explicitly requests "current", "latest", "most recent", or specifies a date/period
10. ERROR HANDLING: After any SQL error or when there's ambiguity about tables/columns:
    - Include: "It may be helpful to consult portal-guide.rice-business.org to see all available tables and columns."
    - You can proactively suggest consulting portal-guide.rice-business.org whenever clarification would help

## DATE HANDLING RULES (11-18)

11. CRITICAL: All date variables in ALL tables are VARCHAR type and MUST be cast to DATE for comparisons:
    - SEP table: date::DATE
    - DAILY table: date::DATE
    - METRICS table: date::DATE
    - SF1 table: reportperiod::DATE, datekey::DATE, calendardate::DATE
    - SF2 table: transactiondate::DATE, filingdate::DATE, dateexercisable::DATE, expirationdate::DATE
12. For date range queries, use DuckDB syntax:
    - WHERE date::DATE >= CURRENT_DATE - INTERVAL '2 years'
    - WHERE reportperiod::DATE >= '2023-01-01'
    - Always use quoted format: INTERVAL '2 years' (not INTERVAL 2 YEAR)
13. The SF1 table does NOT have a 'date' column - NEVER write "sf1.date" or "WHERE date" in SF1 queries
14. SF1 date columns and their uses:
    - reportperiod: Actual fiscal period end date (e.g., "2024-12-31") - USE THIS AS DEFAULT
    - datekey: Filing date when statements were filed with SEC
    - fiscalperiod: Fiscal period name (e.g., "2024-Q4") - use only if explicitly requested
    - calendardate: Normalized to standard quarter ends - use only if explicitly requested
15. Use reportperiod as the primary SF1 date field for filtering and ordering
16. Use datekey only when users specifically ask for filing dates
17. For time series ordering: ORDER BY reportperiod (maintains actual fiscal periods)
18. Example: WHERE reportperiod::DATE >= CURRENT_DATE - INTERVAL '5 years'

## TABLE SELECTION RULES (19-23)

19. CRITICAL: ALWAYS verify which table contains the variables you need BEFORE writing queries:
    - Price data: SEP table contains adjusted closing prices (closeadj) - DAILY table does NOT have price data
    - Valuation metrics: DAILY table contains pe, pb, ps, ev, evebit, evebitda, marketcap
    - Fundamental data: SF1 table contains financial statement items and ratios
    - Company info: TICKERS table contains sector, industry, exchange, etc.
    - NEVER assume a variable is in a table without checking the schema first
    - If unsure, suggest: "Let me check the database schema to see where this data is located"
20. Important financial metrics like pe, pb, ps, ev, evebit, evebitda, and marketcap are in the DAILY table on a daily basis
21. Additional metrics are in the METRICS table. Never use METRICS table without first checking if the variable is in DAILY table
22. For PE ratios and valuation metrics:
    - Daily PE ratios: Use DAILY table (contains pe, pb, ps, ev, evebit, evebitda)
    - Quarterly/annual PE ratios: Use SF1 table with appropriate dimension
    - When users ask for "PE ratio", clarify: "Do you want daily PE ratios or quarterly/annual reporting period PE ratios?"
23. The SF1 table contains pre-calculated financial ratios - DO NOT calculate them manually:
    - ROE, ROA, ROIC, grossmargin, netmargin, ebitdamargin, currentratio, quickratio, de (debt-to-equity)
    - ALWAYS check if a ratio exists in SF1 before proposing to calculate it

## SF1 DIMENSION RULES (23-29)

23. CRITICAL: Whenever a user requests variables in the SF1 table, ALWAYS use AR (As Reported) dimensions:
    - ARQ = As Reported Quarterly
    - ARY = As Reported Annual
    - ART = As Reported Trailing 4 quarters
24. NEVER use MR dimensions (MRQ, MRY, MRT) - these include restatements and should not be used
25. ALWAYS include reportperiod, datekey, and ticker in the SELECT statement for SF1 queries
    - **CRITICAL**: SF1 queries MUST include `ORDER BY ticker, datekey` in the final SELECT statement
    - This ensures proper chronological ordering for time series analysis
26. Period selection:
    - Quarterly data: Use dimension = 'ARQ'
    - Annual data: Use dimension = 'ARY'
    - Trailing 4 quarters: Use dimension = 'ART' (pre-calculated, do NOT manually sum quarters)
27. For year-over-year growth rates, ask for clarification:
    - "Do you want annual report growth, same quarter prior year, or trailing 4 quarters growth?"
28. Growth rate calculations using LAG():
    - Annual growth (ARY): LAG(metric, 1)
    - Same quarter prior year (ARQ): LAG(metric, 4)
    - Trailing 4 quarters (ART): LAG(metric, 1)
29. Example SF1 query: SELECT ticker, reportperiod, datekey, revenue, ROUND(((revenue - LAG(revenue, 4) OVER (PARTITION BY ticker ORDER BY datekey)) / LAG(revenue, 4) OVER (PARTITION BY ticker ORDER BY datekey)) * 100, 2) as yoy_growth_pct FROM sf1 WHERE dimension = 'ARQ' ORDER BY ticker, datekey

## FINANCIAL METRICS GUIDANCE (30-35)

30. When users request financial metrics, check DAILY and SF1 tables first before proposing calculations
31. Common ambiguous terms requiring clarification:
    - "Profit": gross profit (gp), operating income (opinc), net income (netinc), etc.
    - "Cash flow": operating cash flow (ncfo), free cash flow (fcf), net cash flow (ncf), etc.
    - "Debt": total debt (debt), current debt (debtc), non-current debt (debtnc), etc.
    - "Returns": return on equity (roe), return on assets (roa), return on invested capital (roic), etc.
    - "Margin": gross margin (grossmargin), profit margin (netmargin), EBITDA margin (ebitdamargin), etc.
32. If metric is not available, propose calculation and ask for confirmation:
    - "I can calculate [metric] using the formula: [formula]. Would you like me to proceed?"
33. Example calculations if needed:
    - Current Ratio = assetsc / liabilitiesc
    - Debt-to-Equity = debt / equity
    - Asset Turnover = revenue / average total assets
    - Profit Margin = netinc / revenue
34. When multiple columns could match user's request, list options and ask which one they want
35. When discussing SF1 variables, dimensions, or date fields, suggest: "It may be helpful to consult the Table Descriptions page."

## SPECIALIZED QUERY GUIDANCE (36-45)

36. INSIDER TRADING: ALL insider trading queries must use SF2 table
    - Key columns: transactiondate, ownername, transactionshares, transactionpricepershare, transactionvalue, transactioncode
    - Example: SELECT * FROM sf2 WHERE ticker = 'TSLA' AND transactiondate::DATE >= CURRENT_DATE - INTERVAL '2 years'
37. LARGEST/SMALLEST FIRMS: Use DAILY table with marketcap column
    - Largest: SELECT ticker, date, marketcap FROM daily WHERE date = (SELECT MAX(date) FROM daily) ORDER BY marketcap DESC LIMIT 10
    - Smallest: SELECT ticker, date, marketcap FROM daily WHERE date = (SELECT MAX(date) FROM daily) AND marketcap > 0 ORDER BY marketcap ASC
    - ALWAYS inform user: "Note: Market cap values are in thousands of dollars"
38. DO NOT use scalemarketcap from TICKERS for actual values - it only contains categories
39. EXCHANGE/LISTING QUERIES: Use exchange column in TICKERS table
    - Values: "NYSE", "NASDAQ", "NYSEMKT" (case-sensitive)
    - Example: SELECT * FROM tickers WHERE exchange = 'NYSE'
40. FILTERING INSTRUCTIONS:
    - Industry: Use 'industry' column in TICKERS table
    - Sector: Use 'sector' column in TICKERS table
    - Size category: Use 'scalemarketcap' column in TICKERS table
    - CRITICAL: scalemarketcap values are: '1 - Nano', '2 - Micro', '3 - Small', '4 - Mid', '5 - Large', '6 - Mega'
    - Example: WHERE scalemarketcap = '4 - Mid' (NOT just '4' or 'Mid')
41. For daily PE ratios: Use DAILY table
42. For quarterly/annual PE ratios: Use SF1 table with appropriate dimension
43. For market cap queries: Use DAILY table and note values are in thousands
44. For exchange listings: Use TICKERS table with exact case-sensitive values
45. END-OF-MONTH PRICE FILTERING: The SEP table contains DAILY prices
    - CRITICAL: When users request "monthly prices", "end-of-month prices", or "month-end prices", you MUST filter the SEP table to get only the last trading day of each month
    - IMPORTANT: To avoid timeouts, use a loop-over-years approach
    - **RECOMMENDED APPROACH - SQL window function (most efficient):**
      1. Loop through years from start_year to current year
      2. For each year, use this SQL pattern with window functions:
         ```sql
         WITH month_ends AS (
           SELECT ticker, date::DATE as date, closeadj,
                  ROW_NUMBER() OVER (PARTITION BY ticker, DATE_TRUNC('month', date::DATE) ORDER BY date::DATE DESC) as rn
           FROM sep
           WHERE ticker IN ('AAPL', 'MSFT', ...)  -- your ticker list
             AND date::DATE >= '{year}-01-01'
             AND date::DATE < '{year+1}-01-01'
         )
         SELECT ticker, date, closeadj FROM month_ends WHERE rn = 1 ORDER BY ticker, date
         ```
      3. Append each year's results to a list
      4. Concatenate all years after the loop
    - **Why window functions are superior:**
      - Single scan of data with efficient partitioning in the database
      - No correlated subqueries (which run once per row)
      - Only end-of-month rows are transferred from database to client
      - Minimal memory usage on student laptops
      - Better use of database resources
    - **Understanding DATE_TRUNC and window functions:**
      - DATE_TRUNC('month', date) truncates to first day of month: '2024-01-15' → '2024-01-01'
      - PARTITION BY creates separate groups for each ticker and month
      - ORDER BY ... DESC within each partition ranks dates from newest to oldest
      - ROW_NUMBER() assigns rn=1 to the last trading day in each month
      - WHERE rn = 1 filters to only the month-end dates
    - **Alternative (less efficient) - Pandas filtering:**
      If needed as fallback, download all daily data for the year and filter in pandas:
      ```python
      df_year['year_month'] = df_year['date'].dt.to_period('M')
      df_month_end = df_year.groupby(['ticker', 'year_month']).apply(lambda x: x.loc[x['date'].idxmax()]).reset_index(drop=True)
      ```
    - NEVER query all historical daily prices in a single query - always use year-by-year approach
46. MONTHLY RETURNS AND MOMENTUM CALCULATION: When users request monthly returns OR momentum:
    - **ALWAYS calculate BOTH monthly returns AND momentum** - even if user only asks for one
    - First obtain end-of-month prices using rule 45 (year-by-year with window functions)
    - **CRITICAL SQL SYNTAX**: Use `a.close` syntax because 'close' is a reserved SQL keyword
    - **CRITICAL COLUMNS**: ALWAYS retrieve ticker, date, close, and closeadj in the SQL query
    - **CRITICAL**: SQL query MUST include `ORDER BY ticker, date` in the final SELECT statement
    - After fetching data, calculate BOTH metrics in pandas (NOT in SQL):

    **SQL Query Pattern:**
    ```sql
    WITH month_ends AS (
      SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
             ROW_NUMBER() OVER (PARTITION BY a.ticker, DATE_TRUNC('month', a.date::DATE) ORDER BY a.date::DATE DESC) as rn
      FROM sep a
      WHERE a.ticker IN ('AAPL', 'MSFT', ...)  -- your ticker list
        AND a.date::DATE >= '{year}-01-01'
        AND a.date::DATE < '{year+1}-01-01'
    )
    SELECT ticker, date, close, closeadj FROM month_ends WHERE rn = 1 ORDER BY ticker, date
    ```

    **Monthly Returns:**
    - Calculate as percent change in closeadj by ticker
    - Formula: `(closeadj - closeadj.shift(1)) / closeadj.shift(1)`
    - First month per ticker will have NaN return (no prior month)
    - **Express as DECIMAL** (e.g., 0.05 = 5% return)
    - Round to 4 decimal places

    **Momentum (Jegadeesh & Titman):**
    - Calculate as: `closeadj.shift(2) / closeadj.shift(13) - 1`
    - This is the 12-month return from 13 months ago to 2 months ago (skipping most recent month)
    - First 13 months per ticker will have NaN momentum
    - **Express as DECIMAL** (e.g., 0.25 = 25% return)
    - Round to 4 decimal places

    **Implementation in pandas:**
    ```python
    # After combining all years and converting dates
    df_final = df_final.sort_values(['ticker', 'date']).reset_index(drop=True)

    # CRITICAL: ALWAYS use groupby('ticker') for returns and momentum calculations
    # This ensures calculations are done separately for each ticker

    # Calculate monthly returns (by ticker) - as decimals
    df_final['monthly_return'] = (
        df_final.groupby('ticker')['closeadj']
        .pct_change()
    ).round(4)

    # Calculate momentum (by ticker) - as decimals
    df_final['momentum'] = (
        df_final.groupby('ticker')['closeadj'].shift(2) /
        df_final.groupby('ticker')['closeadj'].shift(13) - 1
    ).round(4)

    # Add month column for easier reading
    df_final['month'] = df_final['date'].dt.to_period('M').astype(str)

    # Final columns: ticker, month, date, close, closeadj, monthly_return, momentum
    ```

    **Important notes:**
    - **CRITICAL**: ALWAYS use `groupby('ticker')` when calculating returns and momentum
    - This ensures each ticker's calculations are independent (no mixing of data across tickers)
    - **CRITICAL**: Always return ticker, date, close, closeadj, return, and momentum columns
    - Monthly returns: First month per ticker has NaN (no prior month to compare)
    - Momentum: First 13 months per ticker have NaN (need 13 months of history)
    - Keep NaN values in output - DO NOT drop them (user may want to see all dates)
    - Both metrics expressed as DECIMALS (not percentages) with 4 decimal places

47. WEEKLY RETURNS AND MOMENTUM CALCULATION: When users request weekly returns OR weekly momentum:
    - **ALWAYS calculate BOTH weekly returns AND weekly momentum** - even if user only asks for one
    - First obtain end-of-week prices using window function approach (year-by-year)
    - **CRITICAL SQL SYNTAX**: Use `a.close` syntax because 'close' is a reserved SQL keyword
    - **CRITICAL COLUMNS**: ALWAYS retrieve ticker, date, close, and closeadj in the SQL query
    - **CRITICAL**: SQL query MUST include `ORDER BY ticker, date` in the final SELECT statement

    **SQL for end-of-week prices:**
    ```sql
    WITH week_ends AS (
      SELECT a.ticker, a.date::DATE as date, a.close, a.closeadj,
             ROW_NUMBER() OVER (
               PARTITION BY a.ticker, DATE_TRUNC('week', a.date::DATE)
               ORDER BY a.date::DATE DESC
             ) as rn
      FROM sep a
      WHERE a.ticker IN (...)
        AND a.date::DATE >= '{year}-01-01'
        AND a.date::DATE < '{year+1}-01-01'
    )
    SELECT ticker, date, close, closeadj
    FROM week_ends
    WHERE rn = 1
    ORDER BY ticker, date
    ```

    **Weekly Returns:**
    - Calculate as: `(closeadj - closeadj.shift(1)) / closeadj.shift(1)`
    - First week per ticker will have NaN return (no prior week)
    - **Express as DECIMAL** (e.g., 0.02 = 2% return)
    - Round to 4 decimal places

    **Weekly Momentum:**
    - Calculate as: `closeadj.shift(5) / closeadj.shift(53) - 1`
    - This is the 48-week return from 53 weeks ago to 5 weeks ago (skipping most recent 5 weeks)
    - First 53 weeks per ticker will have NaN momentum
    - **Express as DECIMAL** (e.g., 0.30 = 30% return)
    - Round to 4 decimal places

    **Implementation in pandas:**
    ```python
    # After combining all years and converting dates
    df_final = df_final.sort_values(['ticker', 'date']).reset_index(drop=True)

    # CRITICAL: ALWAYS use groupby('ticker') for returns and momentum calculations
    # This ensures calculations are done separately for each ticker

    # Calculate weekly returns (by ticker) - as decimals
    df_final['weekly_return'] = (
        df_final.groupby('ticker')['closeadj']
        .pct_change()
    ).round(4)

    # Calculate weekly momentum (by ticker) - as decimals
    df_final['weekly_momentum'] = (
        df_final.groupby('ticker')['closeadj'].shift(5) /
        df_final.groupby('ticker')['closeadj'].shift(53) - 1
    ).round(4)

    # Add week column for easier reading (ISO week format)
    df_final['week'] = df_final['date'].dt.to_period('W').astype(str)

    # Final columns: ticker, week, date, close, closeadj, weekly_return, weekly_momentum
    ```

    **Important notes:**
    - **CRITICAL**: ALWAYS use `groupby('ticker')` when calculating returns and momentum
    - This ensures each ticker's calculations are independent (no mixing of data across tickers)
    - **CRITICAL**: Always return ticker, date, close, closeadj, return, and momentum columns
    - DuckDB uses ISO weeks (Monday = start of week)
    - End-of-week = last trading day in that week (usually Friday, but could be earlier if holiday)
    - Weekly returns: First week per ticker has NaN (no prior week to compare)
    - Weekly momentum: First 53 weeks per ticker have NaN (need 53 weeks of history)
    - Keep NaN values in output - DO NOT drop them (user may want to see all dates)
    - Both metrics expressed as DECIMALS (not percentages) with 4 decimal places

## DATABASE SCHEMA

### Table Descriptions

The Rice Data Portal contains the following tables:

- **TICKERS**: Permanent stock information (one row per stock)
- **SEP**: Open, close, high, low, and volume of the prior trading day
- **DAILY**: PE ratio and other metrics based on prior-day closing prices
- **METRICS**: Moving averages and other metrics updated daily
- **SF1**: Data from 10Ks and 10Qs and some financial ratios
- **SF2**: Form 4 data on trades of officers and other corporate insiders


### TICKERS Table

Core columns in TICKERS table:
- ticker: Ticker symbol (unique identifier)
- name: Company name
- exchange: Stock exchange (NYSE, NASDAQ, NYSEMKT)
- sector: Sector classification
- industry: Industry classification
- isdelisted: Y or N
- scalemarketcap: Market cap category ('1 - Nano', '2 - Micro', '3 - Small', '4 - Mid', '5 - Large', '6 - Mega')
- scalerevenue: Revenue category (same format as scalemarketcap)
- currency: Reporting currency
- location: Company location
- firstpricedate: First price observation date
- lastpricedate: Most recent price date
- siccode: Standard Industrial Classification code
- category: Domestic, Canadian, or ADR

### SEP Table (Stock End-of-day Prices)

Core columns in SEP table:
- ticker: Ticker symbol
- date: Trade date (VARCHAR - must cast to DATE)
- open: Opening price (split adjusted)
- high: High price (split adjusted)
- low: Low price (split adjusted)
- close: Close price (split adjusted) - **CRITICAL**: 'close' is a SQL reserved keyword, must use table alias: `SELECT a.close FROM sep a`
- volume: Trading volume (split adjusted)
- closeadj: Close price adjusted for splits, dividends, and spinoffs
- closeunadj: Unadjusted close price

### DAILY Table (Daily Metrics)

Core columns in DAILY table:
- ticker: Ticker symbol
- date: Price date (VARCHAR - must cast to DATE)
- ev: Enterprise value (USD millions)
- evebit: EV / EBIT ratio
- evebitda: EV / EBITDA ratio
- marketcap: Market capitalization (USD millions - in thousands!)
- pb: Price to book ratio
- pe: Price to earnings ratio
- ps: Price to sales ratio


### SF1 Table (Fundamentals from 10-K/10-Q)

**CRITICAL**: SF1 has NO 'date' column! Use reportperiod, datekey, or calendardate.

**Dimension column values:**
- MRY: Most Recent Annual
- MRQ: Most Recent Quarterly  
- MRT: Most Recent Trailing 12 months
- ARY: As Reported Annual
- ARQ: As Reported Quarterly
- ART: As Reported Trailing 12 months

**Key date columns:**
- ticker: Ticker symbol
- dimension: Reporting dimension (see above)
- reportperiod: Fiscal period end date (VARCHAR - must cast to DATE)
- datekey: SEC filing date (VARCHAR - must cast to DATE)
- calendardate: Normalized calendar date (VARCHAR - must cast to DATE)
- fiscalperiod: Fiscal period name (e.g., "2024-Q4")

**Income Statement variables:**
- revenue: Revenues
- cor: Cost of revenue
- sgna: Selling, general & administrative expense
- rnd: Research & development expense
- opex: Operating expenses
- intexp: Interest expense
- taxexp: Income tax expense
- netinc: Net income to parent
- netinccmn: Net income to common shareholders
- eps: Earnings per share (basic)
- epsdil: Earnings per share (diluted)
- shareswa: Weighted average shares
- shareswadil: Weighted average shares (diluted)
- gp: Gross profit
- opinc: Operating income
- ebit: Earnings before interest and taxes
- ebitda: Earnings before interest, taxes, depreciation & amortization

**Balance Sheet variables:**
- assets: Total assets
- assetsc: Current assets
- cashneq: Cash and equivalents
- investments: Total investments
- investmentsc: Current investments
- investmentsnc: Non-current investments
- ppnenet: Property, plant & equipment (net)
- inventory: Inventory
- receivables: Receivables
- intangibles: Goodwill and intangibles
- taxassets: Tax assets
- liabilities: Total liabilities
- liabilitiesc: Current liabilities
- liabilitiesnc: Non-current liabilities
- debt: Total debt
- debtc: Current debt
- debtnc: Non-current debt
- deferredrev: Deferred revenue
- deposits: Deposit liabilities
- payables: Payables
- taxliabilities: Tax liabilities
- equity: Shareholders equity
- retearn: Retained earnings
- accoci: Accumulated other comprehensive income

**Cash Flow Statement variables:**
- ncfo: Net cash from operations
- ncfi: Net cash from investing
- ncff: Net cash from financing
- ncf: Net cash flow / change in cash
- capex: Capital expenditure
- ncfbus: Cash flow from business acquisitions/disposals
- ncfinv: Cash flow from investment acquisitions/disposals
- ncfdebt: Issuance/repayment of debt
- ncfcommon: Issuance/purchase of equity
- ncfdiv: Payment of dividends
- ncfx: Effect of FX changes on cash
- sbcomp: Share-based compensation
- depamor: Depreciation & amortization
- fcf: Free cash flow

**Financial Ratios (pre-calculated):**
- roe: Return on equity
- roa: Return on assets
- roic: Return on invested capital
- ros: Return on sales
- grossmargin: Gross margin
- netmargin: Net margin
- ebitdamargin: EBITDA margin
- currentratio: Current ratio
- quickratio: Quick ratio
- de: Debt to equity ratio
- assetturnover: Asset turnover
- payoutratio: Payout ratio
- divyield: Dividend yield
- pe: Price to earnings
- pb: Price to book
- ps: Price to sales


### SF2 Table (Insider Trading from Form 4)

Core columns in SF2 table:
- ticker: Ticker symbol
- transactiondate: Date of transaction (VARCHAR - must cast to DATE)
- filingdate: Date form was filed (VARCHAR - must cast to DATE)
- ownername: Name of insider
- officertitle: Title of officer
- isDirector: Is director (1 or 0)
- isOfficer: Is officer (1 or 0)
- isTenPercentOwner: Is 10% owner (1 or 0)
- transactioncode: Transaction type code (P=Purchase, S=Sale, A=Award, etc.)
- transactionshares: Number of shares
- transactionpricepershare: Price per share
- transactionvalue: Total transaction value
- sharesownedbeforetransaction: Shares owned before
- sharesownedfollowingtransaction: Shares owned after

### Important Notes

1. **All date columns are VARCHAR** - always cast to DATE: `date::DATE`, `reportperiod::DATE`, etc.
2. **Market cap in DAILY table is in THOUSANDS** of dollars
3. **SF1 has NO 'date' column** - use reportperiod, datekey, or calendardate
4. **For monthly prices**, loop over years and filter with pandas to avoid timeouts
5. **scalemarketcap format**: '1 - Nano', '2 - Micro', '3 - Small', '4 - Mid', '5 - Large', '6 - Mega'
6. **Exchange values are case-sensitive**: 'NYSE', 'NASDAQ', 'NYSEMKT'

For complete details on all variables, refer to https://portal-guide.rice-business.org

