"""
Technical Factors
Moving Average and Volume Ratio factors
"""

import pandas as pd
import numpy as np
from .base import BaseFactor


class MAFactor(BaseFactor):
    """
    Moving Average Factor
    
    Logic: Calculate moving average and boolean 'above_ma' indicator.
    """
    
    def __init__(self, window: int = 20):
        """
        Initialize MA Factor.
        
        Args:
            window: Moving average window (default: 20)
        """
        self.window = window
    
    def name(self) -> str:
        """Return factor name"""
        return f"ma_{self.window}"
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute MA factor.
        
        Requires columns: ts_code, trade_date, close
        
        Args:
            df: DataFrame with stock data
            
        Returns:
            DataFrame with 'ma' and 'above_ma' columns added
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        if 'close' not in df.columns:
            raise ValueError("MAFactor requires 'close' column")
        
        # Ensure trade_date is datetime for sorting
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        
        # Sort by ts_code and trade_date
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
        
        # Calculate moving average grouped by ts_code
        df[f'ma_{self.window}'] = df.groupby('ts_code')['close'].transform(
            lambda x: x.rolling(window=self.window, min_periods=1).mean()
        )
        
        # Boolean indicator: close > ma
        column_name = f'above_ma_{self.window}'
        df[column_name] = (df['close'] > df[f'ma_{self.window}']).astype(int)
        
        return df


class VolumeRatioFactor(BaseFactor):
    """
    Volume Ratio Factor
    
    Logic: Calculate volume / rolling_mean(volume) ratio.
    """
    
    def __init__(self, window: int = 5):
        """
        Initialize Volume Ratio Factor.
        
        Args:
            window: Rolling window for volume mean calculation (default: 5)
        """
        self.window = window
    
    def name(self) -> str:
        """Return factor name"""
        return f"volume_ratio_{self.window}"
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute Volume Ratio factor.
        
        Requires columns: ts_code, trade_date, vol (or volume)
        
        Args:
            df: DataFrame with stock data
            
        Returns:
            DataFrame with 'volume_ratio' column added
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Handle different volume column names
        if 'vol' not in df.columns and 'volume' in df.columns:
            df['vol'] = df['volume']
        elif 'vol' not in df.columns:
            raise ValueError("VolumeRatioFactor requires 'vol' or 'volume' column")
        
        # Ensure trade_date is datetime for sorting
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        
        # Sort by ts_code and trade_date
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
        
        # Calculate rolling mean of volume grouped by ts_code
        rolling_mean_vol = df.groupby('ts_code')['vol'].transform(
            lambda x: x.rolling(window=self.window, min_periods=1).mean()
        )
        
        # Calculate volume ratio: vol / rolling_mean(vol)
        column_name = f'vol_ratio_{self.window}'
        df[column_name] = df['vol'] / rolling_mean_vol.replace(0, np.nan)
        
        # Fill NaN values (when rolling_mean is 0 or NaN) with 1.0
        df[column_name] = df[column_name].fillna(1.0)
        
        return df
