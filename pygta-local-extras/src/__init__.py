"""Local helper utilities for the pygta workspace."""

from pygta_local_extras.io.tabular import csv_to_dataset
from pygta_local_extras.io.tabular import load_dataset_from_csv
from pygta_local_extras.selection.ranges import slice_by_ranges
from pygta_local_extras.selection.ranges import slice_spectral_range
from pygta_local_extras.selection.ranges import slice_time_range

__all__ = [
    "__version__",
    "csv_to_dataset",
    "load_dataset_from_csv",
    "slice_by_ranges",
    "slice_spectral_range",
    "slice_time_range",
]

__version__ = "0.1.0"
