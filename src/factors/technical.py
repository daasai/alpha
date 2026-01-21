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
        # min_periods设置为window，确保只有足够数据点时才计算MA
        df[f'ma_{self.window}'] = df.groupby('ts_code')['close'].transform(
            lambda x: x.rolling(window=self.window, min_periods=self.window).mean()
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
        # 当rolling_mean_vol为0或NaN时，量比应为NaN（表示无法计算）
        column_name = f'vol_ratio_{self.window}'
        df[column_name] = df['vol'] / rolling_mean_vol.replace(0, np.nan)
        # 不填充NaN，保持NaN值（表示零成交量或数据不足）
        
        return df


class BBIFactor(BaseFactor):
    """
    Bull Bear Index (BBI) Factor
    
    Logic: Calculate BBI = (MA(w1) + MA(w2) + MA(w3) + MA(w4)) / 4
    and generate bbi_signal: 1 (Bull) if close > BBI, -1 (Bear) if close < BBI.
    
    Enhanced with N-Day Confirmation Rule:
    - bbi_confirmed_signal: Only signals 1 (Bull) if Close > BBI for N consecutive days.
    - This reduces whipsaw losses in choppy markets.
    """
    
    def __init__(self, ma_windows: list = None, confirmation_days: int = 3):
        """
        Initialize BBI Factor.
        
        Args:
            ma_windows: List of moving average windows for BBI calculation (default: [3, 6, 12, 24])
            confirmation_days: Number of consecutive days required for bull confirmation (default: 3)
        """
        self.ma_windows = ma_windows or [3, 6, 12, 24]
        self.confirmation_days = confirmation_days
        
        # 验证参数
        if len(self.ma_windows) != 4:
            raise ValueError(f"BBIFactor requires exactly 4 MA windows, got {len(self.ma_windows)}")
        if any(w <= 0 for w in self.ma_windows):
            raise ValueError(f"BBIFactor MA windows must be positive, got {self.ma_windows}")
        if self.confirmation_days <= 0:
            raise ValueError(f"BBIFactor confirmation_days must be positive, got {self.confirmation_days}")
    
    def name(self) -> str:
        """Return factor name"""
        return "bbi"
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute BBI factor.
        
        Requires columns: close
        
        Args:
            df: DataFrame with stock data (can be single stock or index data)
            
        Returns:
            DataFrame with 'bbi', 'bbi_signal', and 'bbi_confirmed_signal' columns added
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        if 'close' not in df.columns:
            raise ValueError("BBIFactor requires 'close' column")
        
        # Ensure trade_date is datetime for sorting
        if 'trade_date' in df.columns:
            if df['trade_date'].dtype == 'object':
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
            df = df.sort_values('trade_date').reset_index(drop=True)
        
        # Calculate moving averages using configured windows
        ma_list = []
        for window in self.ma_windows:
            ma = df['close'].rolling(window=window, min_periods=1).mean()
            ma_list.append(ma)
        
        # BBI = (MA1 + MA2 + MA3 + MA4) / 4
        df['bbi'] = sum(ma_list) / len(ma_list)
        
        # Generate signal: 1 (Bull) if close > BBI, -1 (Bear) if close < BBI
        # Use 0 for NaN cases (when BBI cannot be calculated)
        df['bbi_signal'] = np.where(
            df['bbi'].notna(),
            np.where(df['close'] > df['bbi'], 1, -1),
            0
        )
        
        # N-Day Confirmation Rule: bbi_confirmed_signal
        # Strict requirement: Close > BBI for N consecutive days to confirm bull
        # Once any day breaks the condition, reset and require re-confirmation
        # This is stricter and should better filter whipsaw signals
        
        # Create daily bull indicator (True if close > BBI and BBI is valid)
        daily_bull = (df['close'] > df['bbi']) & df['bbi'].notna()
        
        # Initialize confirmed signal array
        confirmed_signal = np.full(len(df), -1, dtype=int)  # Default to -1 (bear)
        
        # Track consecutive bull days
        consecutive_bull_days = 0
        
        for i in range(len(df)):
            if not df['bbi'].notna().iloc[i]:
                # BBI is NaN, keep as -1 (bear, conservative)
                confirmed_signal[i] = -1
                consecutive_bull_days = 0
                continue
            
            is_bull_today = daily_bull.iloc[i]
            
            if is_bull_today:
                # Bull day: increment counter
                consecutive_bull_days += 1
                # Signal is 1 only if we have N+ consecutive bull days
                confirmed_signal[i] = 1 if consecutive_bull_days >= self.confirmation_days else -1
            else:
                # Bear day: reset counter immediately
                consecutive_bull_days = 0
                confirmed_signal[i] = -1
        
        df['bbi_confirmed_signal'] = confirmed_signal
        
        return df
