"""
Optimizer plugin modules for docminify.

This package provides various optimizer implementations for different file types.
"""

from docminify.optimizers.base import Optimizer, OptimizationResult
from docminify.optimizers.pdf_optimizer import PDFOptimizer
from docminify.optimizers.text_optimizer import TextOptimizer
from docminify.optimizers.zip_optimizer import ZipOptimizer
from docminify.optimizers.office_optimizer import OfficeOptimizer

__all__ = [
    "Optimizer",
    "OptimizationResult",
    "PDFOptimizer",
    "TextOptimizer",
    "ZipOptimizer",
    "OfficeOptimizer",
]
