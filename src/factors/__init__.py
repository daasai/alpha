"""
Factor Engine Module - DAAS Alpha v1.2
Decoupled architecture with Strategy Design Pattern
"""

from .base import BaseFactor
from .momentum import RPSFactor
from .technical import MAFactor, VolumeRatioFactor, BBIFactor
from .fundamental import PEProxyFactor
from .engine import FactorPipeline

__all__ = [
    'BaseFactor',
    'RPSFactor',
    'MAFactor',
    'VolumeRatioFactor',
    'BBIFactor',
    'PEProxyFactor',
    'FactorPipeline',
]
