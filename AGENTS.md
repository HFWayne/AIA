# AGENTS.md - AI Agent Coding Guidelines

## Project Overview

This is a Python project for stock/fund data analysis and DCA (Dollar-Cost Averaging) backtesting. It provides:
- Unified data source interface supporting tushare, akshare, and baostock
- DCA backtesting engine with visualization
- CLI tool for running backtests

## Build/Lint/Test Commands

### Running the Application
```bash
# Single fund backtest
python main.py --fund 600036 --name 招商银行

# Compare multiple funds
python main.py --compare --funds 600036,000001 --start 2022-01-01 --end 2024-12-31

# Specify data source
python main.py --fund 600036 --source tushare
```

### Testing
```bash
# Run pytest (if tests exist)
pytest

# Run single test
pytest tests/test_file.py::test_function

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Lint with flake8
flake8 .

# Format with black
black .

# Sort imports
isort .
```

## Code Style Guidelines

### General Principles
- Keep functions small and focused (max ~50 lines)
- Write docstrings for all public functions
- Type hints required for function parameters and return values
- Handle exceptions gracefully - never let the program crash silently

### Import Conventions
```python
# Standard library imports first
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict

# Third-party imports second
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Local imports last
from data_source.fund_data_source import FundDataSource
from backtest.dca_backtest import DCABacktest
```

### Naming Conventions
- **Variables/functions**: snake_case (e.g., `fund_code`, `get_fund_data`)
- **Classes**: PascalCase (e.g., `FundDataSource`, `DCABacktest`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DATA_SOURCE`, `TU_SHARE_TOKEN`)
- **Private methods**: prefix with underscore (e.g., `_get_fund_from_tushare`)

### Type Hints
```python
def get_fund_nav(
    fund_code: str,
    start_date: str,
    end_date: str
) -> Optional[pd.DataFrame]:
    """Get fund NAV data.
    
    Args:
        fund_code: Fund code (e.g., "510300")
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
        
    Returns:
        DataFrame with columns: date, nav, accum_nav, or None on failure
    """
    pass
```

### Error Handling
```python
# Use try-except with specific exception types
try:
    result = self._fetch_data(fund_code)
except ConnectionError as e:
    logger.warning(f"Network error: {e}")
    return None
except ValueError as e:
    logger.error(f"Invalid parameter: {e}")
    raise

# Always log errors at appropriate level
# - DEBUG: Detailed diagnostic info
# - INFO: Confirmation that things are working
# - WARNING: Something unexpected happened, but program can continue
# - ERROR: Serious problem, function couldn't execute
# - CRITICAL: Program may crash
```

### Logging
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.info("Starting backtest for fund: %s", fund_code)
logger.warning("Data source unavailable, trying fallback")
logger.error("Failed to fetch data: %s", error_message)
```

### DataFrame Operations
```python
# Prefer method chaining
df = (
    df.rename(columns={'old': 'new'})
    .dropna()
    .sort_values('date')
)

# Use inplace sparingly
df.dropna(inplace=True)  # OK for large datasets

# Avoid chained indexing
df.loc[df['col'] > 0, 'result'] = 1  # Good
# df['result'][df['col'] > 0] = 1    # Bad
```

### Visualization
```python
# Use English labels for matplotlib to avoid font issues
ax.set_title('Portfolio Value')
ax.set_xlabel('Date')
ax.set_ylabel('Amount')

# Use tight_layout
plt.tight_layout()

# Save figures with dpi
plt.savefig('chart.png', dpi=150, bbox_inches='tight')
```

### Configuration
- All configuration in `data_source/config.py`
- Use environment variables or config file for secrets
- Never hardcode API tokens in source code

### File Organization
```
project/
├── data_source/          # Data source interfaces
│   ├── config.py        # Configuration
│   └── fund_data_source.py
├── backtest/            # Backtesting logic
│   ├── dca_backtest.py
│   └── visualization.py
├── tests/               # Unit tests (if any)
├── main.py             # CLI entry point
└── AGENTS.md           # This file
```

### Git Workflow
- Commit messages: conventional format (feat:, fix:, refactor:, etc.)
- Keep commits atomic and focused
- Push to remote after completing features

### Common Patterns

#### Data Source Fallback
```python
def get_data(self, fund_code: str) -> Optional[pd.DataFrame]:
    sources = ['tushare', 'akshare', 'baostock']
    
    for source in sources:
        try:
            data = self._fetch_from_source(source, fund_code)
            if data is not None:
                return data
        except Exception as e:
            logger.warning(f"{source} failed: {e}")
            continue
    
    return None  # All sources failed
```

#### Class Definition
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class BacktestResult:
    """Result of a backtest run."""
    total_invested: float
    final_value: float
    total_return: float
    return_rate: float
    annual_return: float
    max_drawdown: float
    investment_count: int
    nav_data: pd.DataFrame
    trades: pd.DataFrame
```

### Running Single Tests
```bash
# If using pytest
pytest tests/test_backtest.py::test_dca_calculation -v

# If using unittest
python -m unittest tests.test_backtest.TestDCABacktest.test_dca_calculation
```

### VS Code / IDE Settings (Recommended)
```json
{
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.analysis.typeCheckingMode": "basic",
    "editor.formatOnSave": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```
