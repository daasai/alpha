"""
Factor Engine - Pipeline for sequential factor computation
"""

import pandas as pd
from typing import List
from .base import BaseFactor
from ..logging_config import get_logger

logger = get_logger(__name__)


class FactorPipeline:
    """
    Factor Pipeline for sequential execution of multiple factors.
    
    Usage:
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        result_df = pipeline.run(input_df)
    """
    
    def __init__(self):
        """Initialize an empty factor pipeline"""
        self.factors: List[BaseFactor] = []
    
    def add(self, factor: BaseFactor) -> 'FactorPipeline':
        """
        Add a factor to the pipeline.
        
        Args:
            factor: Factor instance implementing BaseFactor
            
        Returns:
            self for method chaining
        """
        if not isinstance(factor, BaseFactor):
            raise TypeError(f"Factor must be an instance of BaseFactor, got {type(factor)}")
        
        self.factors.append(factor)
        logger.debug(f"Added factor to pipeline: {factor.name()}")
        return self
    
    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sequentially execute all factors in the pipeline.
        
        Args:
            df: Input DataFrame with stock data
            
        Returns:
            DataFrame with all factor values computed and added
        """
        if df.empty:
            logger.warning("FactorPipeline.run: Input DataFrame is empty")
            return df
        
        result_df = df.copy()
        
        logger.info(f"FactorPipeline.run: Starting pipeline with {len(self.factors)} factors on {len(result_df)} rows")
        
        for i, factor in enumerate(self.factors, 1):
            try:
                factor_name = factor.name()
                logger.debug(f"Computing factor {i}/{len(self.factors)}: {factor_name}")
                
                result_df = factor.compute(result_df)
                
                logger.debug(f"Factor {factor_name} computed successfully")
            except Exception as e:
                logger.error(f"Error computing factor {factor.name()}: {e}")
                raise
        
        logger.info(f"FactorPipeline.run: Completed successfully, output shape: {result_df.shape}")
        return result_df
    
    def clear(self) -> 'FactorPipeline':
        """
        Clear all factors from the pipeline.
        
        Returns:
            self for method chaining
        """
        self.factors.clear()
        logger.debug("FactorPipeline cleared")
        return self
    
    def __len__(self) -> int:
        """Return the number of factors in the pipeline"""
        return len(self.factors)
    
    def __repr__(self) -> str:
        """String representation of the pipeline"""
        factor_names = [f.name() for f in self.factors]
        return f"FactorPipeline(factors={factor_names})"
