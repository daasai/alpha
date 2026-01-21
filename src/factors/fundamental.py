"""
Fundamental Factors
PE Proxy Factor for value screening
"""

import pandas as pd
import numpy as np
from .base import BaseFactor


class PEProxyFactor(BaseFactor):
    """
    PE Proxy Factor
    
    Logic: Boolean 'is_undervalued' indicator if 0 < pe_ttm < max_pe.
    """
    
    def __init__(self, max_pe: float = 30.0):
        """
        Initialize PE Proxy Factor.
        
        Args:
            max_pe: Maximum PE threshold (default: 30.0)
        """
        self.max_pe = max_pe
    
    def name(self) -> str:
        """Return factor name"""
        return f"pe_proxy_{self.max_pe}"
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute PE Proxy factor.
        
        Requires columns: pe_ttm
        
        Args:
            df: DataFrame with stock data
            
        Returns:
            DataFrame with 'is_undervalued' column added
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        if 'pe_ttm' not in df.columns:
            raise ValueError("PEProxyFactor requires 'pe_ttm' column")
        
        # Boolean indicator: 0 < pe_ttm < max_pe
        # 显式处理NaN值，确保NaN时is_undervalued=0
        df['is_undervalued'] = (
            df['pe_ttm'].notna() & 
            (df['pe_ttm'] > 0) & 
            (df['pe_ttm'] < self.max_pe)
        ).astype(int)
        
        return df
