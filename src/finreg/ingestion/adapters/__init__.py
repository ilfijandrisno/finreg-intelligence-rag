"""Source adapters package for regulatory data ingestion."""

from finreg.ingestion.adapters.bi_adapter import BankIndonesiaAdapter
from finreg.ingestion.adapters.ojk_adapter import OjkAdapter

__all__ = ["BankIndonesiaAdapter", "OjkAdapter"]
