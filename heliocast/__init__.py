"""
HelioCast-L1: Solar Flare Nowcasting & Forecasting Platform for Aditya-L1.
ISRO Problem Statement 15 Solution.
"""

__version__ = "2.0.0"
__author__ = "HelioCast Team"
__mission__ = "Aditya-L1 (SoLEXS & HEL1OS)"

from heliocast.config import get_settings

__all__ = ["__version__", "__author__", "__mission__", "get_settings"]
