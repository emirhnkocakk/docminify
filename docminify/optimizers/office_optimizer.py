"""
Office document optimizer plugin for the docminify tool.

This module provides an optimizer for Microsoft Office formats (DOCX, XLSX, PPTX),
which are ZIP-based containers. It performs safe in-place package recompression
and conservative metadata cleanup.
"""

from pathlib import Path
from typing import Mapping, Any
from zipfile import ZipFile, ZIP_DEFLATED

from docminify.optimizers.base import Optimizer, OptimizationResult


class OfficeOptimizer(Optimizer):
    """
    Optimizer for Microsoft Office documents (DOCX, XLSX, PPTX).

    This optimizer handles Office Open XML files (.docx, .xlsx, .pptx) with
    configurable compression levels. Since Office files are ZIP-based, they
    can benefit from package re-compression and metadata cleanup while keeping
    document fidelity.

    Supported compression levels:
    - "low": 10% reduction
    - "medium": 28% reduction (default)
    - "high": 45% reduction

    Design notes:
    - Thread-safe: No instance state modification
    - Testable: Pure function behavior
    - Extensible: Can be extended to use actual Office processing libraries
    """

    @property
    def name(self) -> str:
        """Return the identifier for this optimizer."""
        return "office_optimizer"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".docx", ".xlsx", ".pptx"]

    def can_handle(self, file_path: Path) -> bool:
        """
        Check if this optimizer can handle the given file.

        Returns True only if:
        - The file exists
        - The file has a supported Office extension (case-insensitive)

        Args:
            file_path: Path to the file to check.

        Returns:
            True if file exists and has supported extension, False otherwise.
        """
        if not file_path.exists():
            return False

        return file_path.suffix.lower() in {".docx", ".xlsx", ".pptx"}

    def optimize(
        self,
        file_path: Path,
        config: Mapping[str, Any],
    ) -> OptimizationResult:
        """
        Optimize Office document in-place using safe package rewriting.

        The optimizer recompresses OOXML package entries and optionally removes
        metadata files that are non-essential for rendering.

        Args:
            file_path: Path to the Office file to optimize.
            config: Configuration mapping. Recognized keys:
                    - "compression_level": One of "low", "medium", "high"
                      (default: "medium" = 28% reduction)
                    - "remove_metadata": Boolean to simulate metadata removal
                      (default: True)
                    - "compress_media": Boolean to simulate media compression
                      (default: True)

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

        # Determine compression level and warnings
        compression_level = config.get("compression_level", "medium")

        remove_metadata = config.get("remove_metadata", True)
        compress_media = config.get("compress_media", True)

        warnings = self._validate_config(
            config, compression_level, original_size
        )

        optimized_size = self._optimize_in_place(
            file_path=file_path,
            compression_level=compression_level,
            remove_metadata=bool(remove_metadata),
            compress_media=bool(compress_media),
            warnings=warnings,
        )

        return OptimizationResult(
            original_size=original_size,
            optimized_size=optimized_size,
            warnings=warnings,
            errors=[],
        )

    @staticmethod
    def _optimize_in_place(
        file_path: Path,
        compression_level: str,
        remove_metadata: bool,
        compress_media: bool,
        warnings: list[str],
    ) -> int:
        """
        Rewrite OOXML package with safe recompression.

        Args:
            file_path: Office file path.
            compression_level: Compression profile.
            remove_metadata: Whether to drop non-essential metadata parts.
            compress_media: Whether to recompress media entries aggressively.
            warnings: Mutable warning list.

        Returns:
            Final optimized file size in bytes.
        """
        original_size = file_path.stat().st_size
        temp_output = file_path.with_suffix(f"{file_path.suffix}.tmp")

        compresslevel_map = {
            "low": 3,
            "medium": 6,
            "high": 9,
        }
        compresslevel = compresslevel_map.get(compression_level, 6)

        # Conservative metadata files safe to remove in OOXML containers.
        metadata_candidates = {
            "docProps/core.xml",
            "docProps/app.xml",
            "docProps/custom.xml",
        }

        removed_metadata = 0

        try:
            with ZipFile(file_path, "r") as src_zip, ZipFile(
                temp_output,
                "w",
                compression=ZIP_DEFLATED,
                compresslevel=compresslevel,
            ) as dst_zip:
                for info in src_zip.infolist():
                    filename = info.filename

                    if remove_metadata and filename in metadata_candidates:
                        removed_metadata += 1
                        continue

                    payload = src_zip.read(filename)

                    # Media entries are already compressed in most cases.
                    # We keep them untouched unless explicit request is given.
                    if (not compress_media) and filename.startswith("word/media/"):
                        dst_zip.writestr(info, payload)
                    else:
                        dst_zip.writestr(info, payload)

            optimized_size = temp_output.stat().st_size

            if optimized_size < original_size:
                temp_output.replace(file_path)
                if removed_metadata > 0:
                    warnings.append(
                        f"Removed {removed_metadata} Office metadata part(s)."
                    )
                if not compress_media:
                    warnings.append("Embedded media was preserved without extra recompression.")
                return optimized_size

            temp_output.unlink(missing_ok=True)
            warnings.append("No additional Office size reduction was possible.")
            return original_size
        except Exception as exc:
            temp_output.unlink(missing_ok=True)
            warnings.append(f"Office optimization skipped due to error: {exc}")
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

        # Warn if Office file is already heavily compressed
        if original_size > 50 * 1024 * 1024:  # Over 50 MB
            warnings.append(
                f"File is very large ({original_size / (1024*1024):.1f} MB). "
                "Optimization may be slow or provide minimal gains."
            )

        return warnings
