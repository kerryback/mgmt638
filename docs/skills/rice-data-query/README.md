# Rice Data Query Skill

This skill enables Claude Code to query the Rice Business Stock Market Data Portal.

## Setup

### 1. Get Access Token

Visit [https://data-portal.rice-business.org](https://data-portal.rice-business.org) and confirm your Rice email address to receive an access token (JWT).

### 2. Create .env File

In your project directory, create a file named `.env` with your access token:

```
RICE_ACCESS_TOKEN=your_token_here
```

Replace `your_token_here` with the actual token from the Rice Data Portal.

**Note**: The `.env` file should be in your `.gitignore` so it won't be committed to git.

### 3. Install Required Packages

Make sure you have these Python packages installed:

```bash
pip install requests pandas python-dotenv
```

### 4. Copy This Skill Folder

Copy this entire `rice-data-query` folder to your `.claude/skills/` directory:

```
your-project/
├── .env                          # Your access token
├── .claude/
│   └── skills/
│       └── rice-data-query/      # This skill folder
│           ├── SKILL.md          # Main skill file
│           └── README.md         # This file
```

## Usage

Once set up, simply ask Claude Code to fetch data from the Rice stock database:

**Example prompts:**
- "Get the monthly prices for AAPL from 2020 to 2023"
- "Show me the 10 largest tech companies by market cap"
- "Fetch quarterly revenue data for Tesla over the last 5 years"
- "Get insider trading data for Microsoft in the past year"

Claude will automatically:
1. Use the skill to generate the correct SQL query
2. Connect to the Rice Data Portal API using your token
3. Fetch the data and return it as a pandas DataFrame
4. **Ask you for a filename and save the data** as a .parquet file for future use

## What This Skill Provides

- **Complete database schema** for all tables (TICKERS, SEP, DAILY, SF1, SF2)
- **SQL query rules** specific to the Rice Data Portal
- **Direct API connection** code (no separate client library needed)
- **Best practices** for avoiding timeouts and handling large datasets

## Tables Available

- **TICKERS**: Company information (sector, industry, exchange, etc.)
- **SEP**: Daily stock prices (open, close, high, low, volume)
- **DAILY**: Daily metrics (PE ratio, market cap, EV, etc.)
- **SF1**: Fundamentals from 10-K/10-Q filings (revenue, earnings, ratios, etc.)
- **SF2**: Insider trading from Form 4 filings

## Important Notes

1. All date columns are VARCHAR type - must cast to DATE in queries
2. Market cap in DAILY table is in thousands of dollars
3. SF1 table has NO 'date' column - use reportperiod, datekey, or calendardate
4. For large datasets (like monthly prices), use year-by-year queries to avoid timeouts

## More Information

For complete variable descriptions and documentation, visit:
- [https://portal-guide.rice-business.org](https://portal-guide.rice-business.org)
- [https://data-portal.rice-business.org](https://data-portal.rice-business.org)
