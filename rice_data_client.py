#!/usr/bin/env python3
"""
Rice Business Stock Market Data - Python Client

A simple Python client for accessing the Rice Business stock market database
through the Rice Data Portal API from Python environments like Google Colab, 
Jupyter notebooks, etc.

Only requires your Rice Data Portal API key!
"""

import os
import requests
import pandas as pd
import warnings
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import logging
import json

class RiceDataClient:
    """
    Python client for Rice Business Stock Market Data
    
    Usage:
        from rice_data_client import RiceDataClient
        
        # Initialize with access token from Rice Data Portal
        client = RiceDataClient(access_token="your_access_token_here")
        
        # Query data
        df = client.query("SELECT * FROM ndl.tickers WHERE sector = 'Technology' LIMIT 10")
        
        # Or use convenience methods
        tech_stocks = client.search_tickers(sector="Technology", limit=10)
    """
    
    def __init__(self, 
                 api_key: str = None,
                 access_token: str = None,
                 base_url: str = None,
                 debug: bool = False):
        """
        Initialize Rice Data Client
        
        Args:
            api_key: Your Rice Data Portal API key (for backwards compatibility)
            access_token: Your Rice Data Portal access token (JWT from email)
            base_url: Base URL for Rice Data Portal (default: auto-detect or localhost)
            debug: Enable debug logging
        """
        
        # Set up logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        
        # API key/access token from parameter or environment
        # Support both api_key (backwards compatibility) and access_token (preferred)
        self.api_key = access_token or api_key or os.getenv("RICE_ACCESS_TOKEN") or os.getenv("RICE_API_KEY")
        if not self.api_key:
            raise ValueError("Access token required. Set RICE_ACCESS_TOKEN environment variable or pass access_token parameter.")
        
        # Base URL for the Rice Data Portal
        self.base_url = base_url or os.getenv("RICE_DATA_URL", "http://localhost:5000")
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
        
        # Validate API key and get permissions
        self.permissions = self._validate_api_key()
        
        print(f"✅ Connected to Rice Business Stock Market Data")
        print(f"📧 User: {self.permissions.get('email', 'Unknown')}")
        print(f"🔑 Permissions: {', '.join(self.permissions.get('permissions', []))}")
    
    def _validate_api_key(self) -> Dict[str, Any]:
        """Validate API key against Rice Data Portal"""
        
        try:
            # Check if API key works by getting table list
            response = requests.get(
                f"{self.base_url}/api/tables",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'error' not in data:
                    # Extract user info from successful response
                    # For now, return basic permissions
                    return {
                        "email": "verified_user@rice.edu",
                        "permissions": ["read_all", "sql_queries"],
                        "max_rows": 10000,
                        "allowed_tables": ["*"]
                    }
            
            # If API call failed, try demo keys for development
            return self._get_demo_permissions()
            
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"API validation failed: {e}")
            # Fall back to demo keys for development/testing
            return self._get_demo_permissions()
    
    def _get_demo_permissions(self) -> Dict[str, Any]:
        """Get demo permissions for development/testing"""
        
        # Demo API keys for development/testing
        demo_keys = {
            "rice_demo_key_123": {
                "email": "demo@rice.edu",
                "permissions": ["read_all", "sql_queries"],
                "max_rows": 1000,
                "allowed_tables": ["*"]
            },
            "faculty_key_456": {
                "email": "faculty@rice.edu", 
                "permissions": ["read_all", "sql_queries", "unlimited"],
                "max_rows": 50000,
                "allowed_tables": ["*"]
            },
            "student_key_789": {
                "email": "student@rice.edu",
                "permissions": ["read_tickers", "read_daily", "read_sep", "sql_queries"],
                "max_rows": 500,
                "allowed_tables": ["ndl.tickers", "ndl.daily", "ndl.sep"]
            }
        }
        
        if self.api_key in demo_keys:
            return demo_keys[self.api_key]
        else:
            raise ValueError(f"Invalid API key. Please check your Rice Data Portal API key.")
    
    def query(self, sql: str, return_df: bool = True) -> Union[pd.DataFrame, List[Dict]]:
        """
        Execute SQL query against the database through Rice Data Portal
        
        Args:
            sql: SQL SELECT statement
            return_df: Return pandas DataFrame (True) or list of dicts (False)
            
        Returns:
            Query results as DataFrame or list of dictionaries
        """
        
        try:
            # Make API request to Rice Data Portal
            response = requests.post(
                f"{self.base_url}/api/query",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
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
            
            # Convert to requested format
            if return_df:
                # Create DataFrame from API response
                if 'data' in data and 'columns' in data:
                    df = pd.DataFrame(data['data'])
                    if not df.empty and 'columns' in data:
                        # Reorder columns to match query order
                        df = df[data['columns']]
                    print(f"📊 Query returned {len(df)} rows")
                    return df
                else:
                    # Empty result
                    df = pd.DataFrame()
                    print(f"📊 Query returned 0 rows")
                    return df
            else:
                # Return as list of dictionaries
                rows = data.get('data', [])
                print(f"📊 Query returned {len(rows)} rows")
                return rows
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error: {e}")
        except Exception as e:
            raise RuntimeError(f"Query failed: {e}")
    
    # Convenience methods for common operations
    
    def search_tickers(self, ticker: str = None, sector: str = None, 
                      industry: str = None, exchange: str = None,
                      is_delisted: bool = None, limit: int = 50) -> pd.DataFrame:
        """Search for tickers with filters"""
        
        conditions = []
        if ticker:
            conditions.append(f"ticker ILIKE '%{ticker}%'")
        if sector:
            conditions.append(f"sector ILIKE '%{sector}%'")
        if industry:
            conditions.append(f"industry ILIKE '%{industry}%'")
        if exchange:
            conditions.append(f"exchange ILIKE '%{exchange}%'")
        if is_delisted is not None:
            conditions.append(f"isdelisted = '{'Y' if is_delisted else 'N'}'")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
        SELECT ticker, name, sector, industry, exchange, isdelisted, 
               location, currency, firstpricedate, lastpricedate
        FROM ndl.tickers 
        WHERE {where_clause}
        ORDER BY ticker
        LIMIT {limit}
        """
        
        return self.query(sql)
    
    def get_ticker_details(self, ticker: str) -> pd.DataFrame:
        """Get detailed information for a specific ticker"""
        sql = f"SELECT * FROM ndl.tickers WHERE ticker = '{ticker.upper()}'"
        return self.query(sql)
    
    def get_daily_data(self, ticker: str = None, start_date: str = None, 
                      end_date: str = None, limit: int = 100) -> pd.DataFrame:
        """Get daily metrics data"""
        conditions = []
        
        if ticker:
            conditions.append(f"ticker = '{ticker.upper()}'")
        if start_date:
            conditions.append(f"date >= '{start_date}'")
        if end_date:
            conditions.append(f"date <= '{end_date}'")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
        SELECT * FROM ndl.daily 
        WHERE {where_clause}
        ORDER BY ticker, date DESC
        LIMIT {limit}
        """
        
        return self.query(sql)
    
    def get_price_data(self, ticker: str = None, start_date: str = None,
                      end_date: str = None, limit: int = 100) -> pd.DataFrame:
        """Get price data from SEP table"""
        conditions = []
        
        if ticker:
            conditions.append(f"ticker = '{ticker.upper()}'")
        if start_date:
            conditions.append(f"date >= '{start_date}'")
        if end_date:
            conditions.append(f"date <= '{end_date}'")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
        SELECT ticker, date, open, high, low, close, volume, closeadj
        FROM ndl.sep 
        WHERE {where_clause}
        ORDER BY ticker, date DESC
        LIMIT {limit}
        """
        
        return self.query(sql)
    
    def get_fundamentals(self, ticker: str = None, dimension: str = "ARY",
                        limit: int = 100) -> pd.DataFrame:
        """Get fundamental data from SF1 table"""
        conditions = [f"dimension = '{dimension}'"]
        
        if ticker:
            conditions.append(f"ticker = '{ticker.upper()}'")
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
        SELECT ticker, calendardate, dimension, revenue, netinc, 
               assets, equity, marketcap, pe, pb, ps
        FROM ndl.sf1 
        WHERE {where_clause}
        ORDER BY ticker, calendardate DESC
        LIMIT {limit}
        """
        
        return self.query(sql)
    
    def list_sectors(self) -> pd.DataFrame:
        """List all sectors with ticker counts"""
        sql = """
        SELECT sector, COUNT(*) as ticker_count
        FROM ndl.tickers 
        WHERE sector IS NOT NULL AND sector != ''
        GROUP BY sector
        ORDER BY ticker_count DESC
        """
        
        return self.query(sql)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        # Total tickers
        total = self.query("SELECT COUNT(*) as count FROM ndl.tickers", return_df=False)
        stats['total_tickers'] = total[0]['count'] if total else 0
        
        # Active tickers
        active = self.query("SELECT COUNT(*) as count FROM ndl.tickers WHERE isdelisted = 'N'", return_df=False)
        stats['active_tickers'] = active[0]['count'] if active else 0
        
        # Top exchanges
        exchanges = self.query("""
            SELECT exchange, COUNT(*) as count 
            FROM ndl.tickers 
            WHERE exchange IS NOT NULL 
            GROUP BY exchange 
            ORDER BY count DESC 
            LIMIT 5
        """, return_df=False)
        stats['top_exchanges'] = exchanges
        
        return stats
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tables",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('tables', [])
            else:
                return []
        except:
            return []

# Convenience function for quick setup
def connect(access_token: str = None, api_key: str = None, base_url: str = None) -> RiceDataClient:
    """
    Quick connection to Rice Business Stock Market Data
    
    Args:
        access_token: Your Rice Data Portal access token (JWT from email)
        api_key: Your Rice Data Portal API key (for backwards compatibility)
        base_url: Base URL for Rice Data Portal (optional)
    
    Returns:
        Connected RiceDataClient instance
    """
    return RiceDataClient(access_token=access_token, api_key=api_key, base_url=base_url)