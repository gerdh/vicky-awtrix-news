"""Information collectors for Vicky.

Collectors convert external data sources into one common item format so the
news engine can rank RSS, Victron, Tesla, mining and market events together.
"""

from .base import Collector, make_item

__all__ = ["Collector", "make_item"]
