# Merge Skill

Expert guidance for merging financial datasets with different frequencies and proper date alignment.

## What This Skill Does

- Provides patterns for merging weekly returns with SF1 fundamentals
- Ensures proper date alignment to avoid look-ahead bias
- Handles forward filling of fundamental data
- Will expand to cover other merge scenarios (monthly, daily, etc.)

## Key Features

### Weekly + SF1 Merge Pattern

1. **Date Alignment**: Aligns SF1 `datekey` with the first Monday AFTER filing
2. **Week Start Calculation**: Converts end-of-week dates to week start dates
3. **Forward Filling**: Propagates fundamental values to subsequent weeks

## When To Use

Use this skill when you need to:
- Merge weekly return data with quarterly SF1 fundamentals
- Combine datasets with different time frequencies
- Ensure proper date alignment for empirical finance research
- Avoid look-ahead bias in backtesting

## Installation

Place this folder in `.claude/skills/merge/` within your course directory.

## Example Usage

"Merge my weekly returns data with quarterly ROE from SF1"

The skill will guide you through:
1. Preparing the SF1 datekey alignment
2. Creating week_start columns in both datasets
3. Performing the merge with proper forward filling

## Prerequisites

- Pandas installed
- Weekly returns data (from rice-data-query skill)
- SF1 fundamental data (from rice-data-query skill)
