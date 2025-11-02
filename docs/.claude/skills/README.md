# Claude Skills for MGMT 638 - Quantitative Equity Strategies

This directory contains specialized skills that Claude Code can invoke to help students with specific tasks in quantitative finance and equity analysis.

## What Are Skills?

Skills are modular capabilities that Claude automatically activates when relevant to the student's request. Unlike the old CLAUDE.md approach (which loaded all instructions into every conversation), skills are **invoked on-demand**, saving context window space for actual work.

## Available Skills

### 🗄️ rice-data-query
**When activated**: Student needs to fetch data from Rice Data Portal
**Purpose**: SQL expert for writing DuckDB queries to get stock market data
**Key feature**: Automatically prompts to save results as Parquet files
**Use cases**:
- "Get monthly prices for Apple from 2020-2024"
- "Fetch quarterly ROE for tech stocks"
- "Get daily market cap for S&P 500 companies"

### 🔀 frequency-merge
**When activated**: Student needs to combine data with different time frequencies
**Purpose**: Expert in merging daily/monthly/quarterly/annual datasets
**Key feature**: Handles point-in-time correctness and forward-fill logic
**Use cases**:
- "Merge daily prices with quarterly fundamentals"
- "Combine monthly returns with annual financial statements"
- "Align daily valuations with quarterly earnings"

### 📈 momentum-strategy
**When activated**: Student needs to build momentum-based trading strategies
**Purpose**: Expert in momentum signals, portfolio formation, and backtesting
**Key feature**: Implements standard academic momentum strategies
**Use cases**:
- "Calculate 12-month momentum skipping the most recent month"
- "Form quintile portfolios based on past returns"
- "Backtest a momentum long-short strategy"

### 📊 factor-models
**When activated**: Student needs to work with factor models or multi-factor strategies
**Purpose**: Expert in Fama-French factors, quality factors, and factor regressions
**Key feature**: Implements standard factor construction and analysis
**Use cases**:
- "Build SMB and HML factors"
- "Run a Fama-French 3-factor regression"
- "Create a quality minus junk factor portfolio"
- "Construct a multi-factor composite score"

### 📑 xlsx
**When activated**: Student needs to create or analyze Excel spreadsheets
**Purpose**: Comprehensive spreadsheet creation, editing, and analysis
**Key feature**: Financial modeling best practices and formula management
**Use cases**:
- "Create an Excel model with my analysis results"
- "Format this data as a professional financial model"
- "Add formulas and charts to this spreadsheet"

## How Skills Work

1. **Automatic Activation**: Claude reads the skill's description and automatically invokes it when relevant
2. **Context Efficiency**: Only the relevant skill is loaded, not all instructions
3. **Composable**: Multiple skills can work together (e.g., rice-data-query → frequency-merge → momentum-strategy)
4. **Discoverable**: Students don't need to know skills exist - Claude uses them automatically

## For Instructors: Adding New Skills

To create a new skill:

1. Create a directory: `.claude/skills/skill-name/`
2. Add a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name
description: "When to use this skill and what it does"
---

# Skill Content

Instructions, examples, and best practices...
```

3. Git commit the new skill - it's automatically available to all students

## Migration from CLAUDE.md

The old `.claude/CLAUDE.md` file contained SQL expertise that was loaded into **every** conversation. This has been replaced with the `rice-data-query` skill, which is only loaded when students need to query the database.

**Benefits**:
- 158 lines of SQL rules only load when needed
- Students working with local files don't waste context on SQL instructions
- Multiple specialized skills instead of one monolithic instruction file
- Easier to maintain and update specific workflows

## For Students: Working with Local Data

Once you've fetched data from Rice Data Portal:
1. The `rice-data-query` skill will prompt you to save it as a Parquet file
2. In future sessions, just load the Parquet file with pandas
3. Claude won't activate the SQL skill unless you explicitly request new data from the portal

This workflow is much more efficient and mirrors real-world practice where you fetch data once and analyze it multiple times.
