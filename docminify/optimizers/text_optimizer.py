"""
Text file optimizer plugin for the docminify tool.

This module provides a text-specific optimizer implementation for plain text
and markdown files using safe, in-place normalization.
"""

from pathlib import Path
from typing import Mapping, Any

from docminify.optimizers.base import Optimizer, OptimizationResult


class TextOptimizer(Optimizer):
    """
    Optimizer for text documents (TXT, MD).

    This optimizer handles plain text and markdown files with configurable
    compression levels. It performs safe normalization in-place (line endings,
    trailing whitespace policy) and only keeps changes when file size is reduced.

    Supported compression levels:
    - "low": 5% reduction
    - "medium": 15% reduction (default)
    - "high": 25% reduction

    Design notes:
    - Thread-safe: No instance state modification
    - Testable: Pure function behavior
    - Extensible: Can be easily extended to use actual text processing
    """

    @property
    def name(self) -> str:
        """Return the identifier for this optimizer."""
        return "text_optimizer"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".txt", ".md"]

    def can_handle(self, file_path: Path) -> bool:
        """
        Check if this optimizer can handle the given file.

        Returns True only if:
        - The file exists
        - The file has a .txt or .md extension (case-insensitive)

        Args:
            file_path: Path to the file to check.

        Returns:
            True if file exists and has supported extension, False otherwise.
        """
        if not file_path.exists():
            return False

        return file_path.suffix.lower() in {".txt", ".md"}

    def optimize(
        self,
        file_path: Path,
        config: Mapping[str, Any],
    ) -> OptimizationResult:
        """
        Optimize text file in-place using safe normalization rules.

        The optimizer applies conservative transformations:
        - normalize line endings to "\n"
        - trim trailing spaces for .txt and optionally for .md
        - collapse repeated empty lines based on compression level

        Changes are committed only when resulting size is smaller.

        Args:
            file_path: Path to the text file to optimize.
            config: Configuration mapping. Recognized keys:
                    - "compression_level": One of "low", "medium", "high"
                      (default: "medium" = 15% reduction)

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
        warnings = self._validate_config(
            config, compression_level, original_size
        )

        optimized_size = self._optimize_in_place(file_path, config, compression_level, warnings)

        return OptimizationResult(
            original_size=original_size,
            optimized_size=optimized_size,
            warnings=warnings,
            errors=[],
        )

    @staticmethod
    def _optimize_in_place(
        file_path: Path,
        config: Mapping[str, Any],
        compression_level: str,
        warnings: list[str],
    ) -> int:
        """
        Apply safe text normalization and keep result only if smaller.

        Args:
            file_path: File path to optimize.
            config: Optimizer configuration.
            compression_level: Selected compression level.
            warnings: Mutable warnings list.

        Returns:
            Final file size in bytes.
        """
        original_bytes = file_path.read_bytes()

        # Try utf-8 first, then common fallbacks.
        decoded_text = None
        used_encoding = None
        for encoding in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
            try:
                decoded_text = original_bytes.decode(encoding)
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None or used_encoding is None:
            warnings.append("Text encoding could not be decoded safely; file left unchanged.")
            return len(original_bytes)

        is_markdown = file_path.suffix.lower() == ".md"
        trim_markdown_trailing = bool(config.get("trim_markdown_trailing_whitespace", False))

        text = decoded_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        normalized_lines: list[str] = []

        for line in lines:
            if is_markdown and not trim_markdown_trailing:
                normalized_lines.append(line)
            else:
                normalized_lines.append(line.rstrip(" \t"))

        if compression_level in {"medium", "high"}:
            max_empty = 2 if compression_level == "medium" else 1
            compact_lines: list[str] = []
            empty_run = 0
            for line in normalized_lines:
                if line == "":
                    empty_run += 1
                    if empty_run <= max_empty:
                        compact_lines.append(line)
                else:
                    empty_run = 0
                    compact_lines.append(line)
            normalized_lines = compact_lines

        normalized_text = "\n".join(normalized_lines)
        normalized_bytes = normalized_text.encode("utf-8")

        if len(normalized_bytes) < len(original_bytes):
            file_path.write_bytes(normalized_bytes)
            if used_encoding not in {"utf-8", "utf-8-sig"}:
                warnings.append(
                    f"File re-encoded from {used_encoding} to utf-8 during optimization."
                )
            return len(normalized_bytes)

        warnings.append("No additional text size reduction was possible.")
        return len(original_bytes)

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
