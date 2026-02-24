"""
PDF optimizer plugin for the docminify tool.

This module provides a PDF-specific optimizer implementation that simulates
compression based on configurable compression levels.
"""

from pathlib import Path
from typing import Mapping, Any

from docminify.optimizers.base import Optimizer, OptimizationResult


class PdfOptimizer(Optimizer):
    """
    Optimizer for PDF documents.

    This optimizer handles PDF files with configurable compression levels.
    Currently simulates optimization without modifying the actual file,
    making it suitable for testing and development.

    Supported compression levels:
    - "low": 10% reduction
    - "medium": 20% reduction (default)
    - "high": 35% reduction

    Design notes:
    - Thread-safe: No instance state modification
    - Testable: Pure function behavior
    - Extensible: Can be easily extended to use actual PDF libraries
    """

    @property
    def name(self) -> str:
        """Return the identifier for this optimizer."""
        return "pdf_optimizer"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".pdf"]

    def can_handle(self, file_path: Path) -> bool:
        """
        Check if this optimizer can handle the given file.

        Returns True only if:
        - The file exists
        - The file has a .pdf extension (case-insensitive)

        Args:
            file_path: Path to the file to check.

        Returns:
            True if file exists and has .pdf extension, False otherwise.
        """
        if not file_path.exists():
            return False

        return file_path.suffix.lower() == ".pdf"

    def optimize(
        self,
        file_path: Path,
        config: Mapping[str, Any],
    ) -> OptimizationResult:
        """
        Simulate PDF optimization based on compression level.

        This method validates the input file and simulates PDF compression
        without modifying the actual file. It supports configurable compression
        levels to demonstrate different optimization scenarios.

        Args:
            file_path: Path to the PDF file to optimize.
            config: Configuration mapping. Recognized keys:
                    - "compression_level": One of "low", "medium", "high"
                      (default: "medium" = 20% reduction)

        Returns:
            OptimizationResult with optimization metrics and any warnings.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file is not a file or cannot be accessed.
        """
        # Validate file
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Get original size
        original_size = file_path.stat().st_size

        # Determine compression level and calculate reduction percentage
        compression_level = config.get("compression_level", "medium")
        reduction_percentage = self._get_reduction_percentage(compression_level)
        warnings = self._validate_config(
            config, compression_level, original_size
        )

        # Calculate optimized size
        optimized_size = int(original_size * (1 - reduction_percentage / 100))
        optimized_size = max(0, optimized_size)

        return OptimizationResult(
            original_size=original_size,
            optimized_size=optimized_size,
            warnings=warnings,
            errors=[],
        )

    @staticmethod
    def _get_reduction_percentage(compression_level: str) -> float:
        """
        Map compression level to reduction percentage.

        Args:
            compression_level: One of "low", "medium", "high", or custom value.

        Returns:
            The reduction percentage (0-100) for the given level.
            Returns default (20%) for unrecognized levels.
        """
        compression_map = {
            "low": 10.0,
            "medium": 20.0,
            "high": 35.0,
        }

        return compression_map.get(compression_level, 20.0)

    @staticmethod
    def _validate_config(
        config: Mapping[str, Any],
        compression_level: str,
        original_size: int,
    ) -> list[str]:
        """
        Validate configuration and collect warnings.

        Args:
            config: Configuration mapping to validate.
            compression_level: The compression level string used.
            original_size: Original file size in bytes.

        Returns:
            List of warning messages. Empty if no warnings.
        """
        warnings = []

        # Check for invalid compression level
        valid_levels = {"low", "medium", "high"}
        if compression_level not in valid_levels:
            warnings.append(
                f"Invalid compression_level '{compression_level}'. "
                f"Use one of {valid_levels}. Using default (medium)."
            )

        # Check for extremely small files
        if original_size < 1024:  # Less than 1 KB
            warnings.append(
                f"File is very small ({original_size} bytes). "
                "Compression may not provide significant benefits."
            )

        return warnings
    
