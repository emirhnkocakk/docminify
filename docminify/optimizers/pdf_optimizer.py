"""
PDF optimizer plugin for the docminify tool.

This module provides a PDF-specific optimizer implementation that performs
lossless PDF optimization when pikepdf is available.
"""

from pathlib import Path
from typing import Mapping, Any

from docminify.optimizers.base import Optimizer, OptimizationResult

try:
    import pikepdf
except ImportError:  # pragma: no cover - handled via runtime warning
    pikepdf = None


class PDFOptimizer(Optimizer):
    """
    Optimizer for PDF documents.

    This optimizer handles PDF files with configurable compression levels.
    When pikepdf is available, it performs a lossless optimization pass by
    rewriting and recompressing streams without rasterizing page content.

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
        Optimize PDF using lossless stream recompression.

        This method validates the input file and performs lossless PDF rewrite
        when pikepdf is installed. If optimization does not reduce size,
        the original file is preserved.

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

        # Determine compression level for save strategy and gather warnings
        compression_level = config.get("compression_level", "medium")
        warnings = self._validate_config(
            config, compression_level, original_size
        )

        # If pikepdf is missing, do not risk file corruption. Return unchanged file.
        if pikepdf is None:
            warnings.append(
                "pikepdf is not installed. Returning original PDF without optimization."
            )
            return OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                warnings=warnings,
                errors=[],
            )

        optimized_size = self._optimize_with_pikepdf(file_path, compression_level, warnings)

        return OptimizationResult(
            original_size=original_size,
            optimized_size=optimized_size,
            warnings=warnings,
            errors=[],
        )

    @staticmethod
    def _optimize_with_pikepdf(
        file_path: Path,
        compression_level: str,
        warnings: list[str],
    ) -> int:
        """
        Optimize PDF file in-place using pikepdf in a lossless way.

        Args:
            file_path: PDF path to optimize.
            compression_level: One of "low", "medium", "high".
            warnings: Mutable warning list.

        Returns:
            Final optimized file size in bytes.
        """
        original_size = file_path.stat().st_size
        temp_output = file_path.with_suffix(".tmp.optimized.pdf")

        # Tune save behavior per level while preserving visual fidelity.
        linearize = compression_level == "high"
        object_stream_mode = (
            pikepdf.ObjectStreamMode.preserve
            if compression_level == "low"
            else pikepdf.ObjectStreamMode.generate
        )

        try:
            with pikepdf.open(file_path) as pdf:
                pdf.save(
                    temp_output,
                    compress_streams=True,
                    recompress_flate=True,
                    object_stream_mode=object_stream_mode,
                    linearize=linearize,
                    preserve_pdfa=True,
                )

            optimized_size = temp_output.stat().st_size

            # Only replace file when optimization is beneficial.
            if optimized_size < original_size:
                temp_output.replace(file_path)
                return optimized_size

            warnings.append("PDF is already optimized or could not be reduced further.")
            temp_output.unlink(missing_ok=True)
            return original_size
        except Exception as exc:
            warnings.append(f"Lossless PDF optimization skipped: {exc}")
            temp_output.unlink(missing_ok=True)
            return original_size

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
    
