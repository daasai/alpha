"""
Base Factor Abstract Class
Strategy Design Pattern - Base interface for all factors
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseFactor(ABC):
    """
    Abstract base class for all factors.
    All factors must implement compute() and name() methods.
    """
    
    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute the factor values and add them to the dataframe.
        
        Args:
            df: Input DataFrame with stock data
            
        Returns:
            DataFrame with factor values added as new columns
        """
        pass
    
    @abstractmethod
    def name(self) -> str:
        """
        Return the name of the factor.
        
        Returns:
            Factor name as string
        """
        pass
