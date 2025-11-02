---
name: rice-data-query
description: "SQL expert for Rice Data Portal queries using DuckDB SQL. Use this skill when students need to fetch data from the Rice stock market database (tickers, prices, fundamentals, insider trades, valuation metrics, etc.). Do NOT use this skill for analyzing local CSV/Parquet files that are already saved."
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

## How to Execute SQL Queries

Use this Python code to send SQL queries to the Rice Data Portal:

```python
def query_rice_data(sql):
    """Execute SQL query against Rice Data Portal"""
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

    # Convert to DataFrame
    if 'data' in data and 'columns' in data:
        df = pd.DataFrame(data['data'])
        if not df.empty and 'columns' in data:
            df = df[data['columns']]
        print(f"Query returned {len(df)} rows")
        return df
    else:
        print(f"Query returned 0 rows")
        return pd.DataFrame()

# Example usage:
# sql = "SELECT * FROM tickers WHERE sector = 'Technology' LIMIT 10"
# df = query_rice_data(sql)
```

## CRITICAL: Save Data After Each Query

After successfully fetching data from the Rice Data Portal:

1. **Ask the user for a filename**: "What filename would you like to use to save this data? (e.g., 'tech_stocks.parquet')"
2. **Save as Parquet format**: Use `df.to_parquet(filename)` to save the DataFrame
3. **Confirm the save**: Let the user know the data has been saved and where

Example:
```python
# After querying data
df = client.query(sql)

# Save to parquet
filename = "momentum_data.parquet"  # Use the filename from user
df.to_parquet(filename)
print(f"Data saved to {filename} ({len(df)} rows)")
```

This allows students to work with the data in future sessions without re-querying the database.

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

23. The dimension column in SF1 controls reporting period and revision status:
    - MR = Most Recent (including restatements)
    - AR = As Originally Reported (no revisions)
    - Y = Annual, Q = Quarterly, T = Trailing 4 quarters
24. When to use AR dimensions:
    - User asks for filing dates ("when reports were filed/issued/published/submitted")
    - User asks for "as originally reported" data
    - Use: ARY (annual), ARQ (quarterly), ART (trailing 4Q)
25. When to use MR dimensions (DEFAULT):
    - User does NOT ask for filing dates or as-originally-reported data
    - Use: MRY (annual), MRQ (quarterly), MRT (trailing 4Q)
26. Period selection:
    - Quarterly data: Use ARQ or MRQ
    - Annual data: Use ARY or MRY
    - Trailing 4 quarters: Use ART or MRT (pre-calculated, do NOT manually sum quarters)
27. For year-over-year growth rates, ask for clarification:
    - "Do you want annual report growth, same quarter prior year, or trailing 4 quarters growth?"
28. Growth rate calculations using LAG():
    - Annual growth (MRY): LAG(metric, 1)
    - Same quarter prior year (MRQ): LAG(metric, 4)
    - Trailing 4 quarters (MRT): LAG(metric, 1)
29. Example: ROUND(((revenue - LAG(revenue, 4) OVER (PARTITION BY ticker ORDER BY reportperiod)) / LAG(revenue, 4) OVER (PARTITION BY ticker ORDER BY reportperiod)) * 100, 2) as yoy_growth_pct

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
- close: Close price (split adjusted)
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

