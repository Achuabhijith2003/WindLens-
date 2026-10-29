"""Elexon BMRS API integration modules for WindLens."""

from .client import ElexonClient, ElexonAPIError, ElexonTimeoutError, ElexonHTTPStatusError, ElexonConnectionError
from .models import FuelHHRecord, ExplorationReport
from .fuelhh import fetch_fuelhh_windowed, analyze_fuelhh_records, generate_date_windows
from .windfor import WindforRecord, analyze_windfor_records

__all__ = [
    "ElexonClient",
    "ElexonAPIError",
    "ElexonTimeoutError",
    "ElexonHTTPStatusError",
    "ElexonConnectionError",
    "FuelHHRecord",
    "ExplorationReport",
    "fetch_fuelhh_windowed",
    "analyze_fuelhh_records",
    "generate_date_windows",
    "WindforRecord",
    "analyze_windfor_records",
]

