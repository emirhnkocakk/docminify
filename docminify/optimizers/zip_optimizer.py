"""
ZIP archive optimizer plugin for the docminify tool.

This module provides a ZIP-specific optimizer implementation using real
re-compression and optional duplicate entry removal.
"""

import hashlib
from pathlib import Path
from typing import Mapping, Any
from zipfile import ZipFile, ZIP_DEFLATED

from docminify.optimizers.base import Optimizer, OptimizationResult


class ZipOptimizer(Optimizer):
    """
    Optimizer for ZIP archives.

    This optimizer handles ZIP files with configurable compression levels.
    It performs in-place re-compression and optional duplicate payload removal.

    Supported compression levels:
    - "low": 15% reduction
    - "medium": 25% reduction (default)
    - "high": 40% reduction

    Design notes:
    - Thread-safe: No instance state modification
    - Testable: Pure function behavior
    - Extensible: Can be easily extended to use actual ZIP processing libraries
    """

    @property
    def name(self) -> str:
        """Return the identifier for this optimizer."""
        return "zip_optimizer"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".zip"]

    def can_handle(self, file_path: Path) -> bool:
        """
        Check if this optimizer can handle the given file.

        Returns True only if:
        - The file exists
        - The file has a .zip extension (case-insensitive)

        Args:
            file_path: Path to the file to check.

        Returns:
            True if file exists and has .zip extension, False otherwise.
        """
        if not file_path.exists():
            return False

        return file_path.suffix.lower() == ".zip"

    def optimize(
        self,
        file_path: Path,
        config: Mapping[str, Any],
    ) -> OptimizationResult:
        """
        Optimize ZIP archive in-place via recompression and deduplication.

        The optimizer rewrites archive entries using DEFLATE and can skip
        duplicated payload entries (same content hash), while preserving a
        valid ZIP structure.

        Args:
            file_path: Path to the ZIP file to optimize.
            config: Configuration mapping. Recognized keys:
                    - "compression_level": One of "low", "medium", "high"
                      (default: "medium" = 25% reduction)
                    - "remove_duplicates": Boolean to simulate duplicate removal
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
        remove_duplicates = config.get("remove_duplicates", True)

        warnings = self._validate_config(
            config, compression_level, original_size
        )

        optimized_size = self._optimize_in_place(
            file_path,
            compression_level=compression_level,
            remove_duplicates=bool(remove_duplicates),
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
        remove_duplicates: bool,
        warnings: list[str],
    ) -> int:
        """
        Rewrite zip archive in-place with configurable compression level.

        Args:
            file_path: Archive file path.
            compression_level: Compression level profile.
            remove_duplicates: Whether to skip duplicate file payloads.
            warnings: Mutable warning list.

        Returns:
            Final archive size in bytes.
        """
        original_size = file_path.stat().st_size
        temp_output = file_path.with_suffix(".tmp.optimized.zip")

        compresslevel_map = {
            "low": 3,
            "medium": 6,
            "high": 9,
        }
        compresslevel = compresslevel_map.get(compression_level, 6)

        try:
            seen_hashes: set[str] = set()
            removed_duplicates = 0

            with ZipFile(file_path, "r") as src_zip, ZipFile(
                temp_output,
                "w",
                compression=ZIP_DEFLATED,
                compresslevel=compresslevel,
            ) as dst_zip:
                for info in src_zip.infolist():
                    if info.is_dir():
                        dst_zip.writestr(info, b"")
                        continue

                    payload = src_zip.read(info.filename)

                    if remove_duplicates:
                        payload_hash = hashlib.sha256(payload).hexdigest()
                        if payload_hash in seen_hashes:
                            removed_duplicates += 1
                            continue
                        seen_hashes.add(payload_hash)

                    dst_zip.writestr(info, payload)

            optimized_size = temp_output.stat().st_size

            if optimized_size < original_size:
                temp_output.replace(file_path)
                if removed_duplicates > 0:
                    warnings.append(
                        f"Removed {removed_duplicates} duplicate file entries from archive."
                    )
                return optimized_size

            temp_output.unlink(missing_ok=True)
            warnings.append("No additional ZIP size reduction was possible.")
            return original_size
        except Exception as exc:
            temp_output.unlink(missing_ok=True)
            warnings.append(f"ZIP optimization skipped due to error: {exc}")
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
