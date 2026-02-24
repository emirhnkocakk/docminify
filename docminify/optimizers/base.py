"""
Core optimizer interface for the docminify plugin-based architecture.

This module defines the abstract base classes and data structures for document
optimization. All optimizer implementations should inherit from the Optimizer
class and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Mapping, Any


@dataclass
class OptimizationResult:
    """
    Represents the result of an optimization operation.
    """

    original_size: int
    optimized_size: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    reduction_bytes: int = field(init=False)
    reduction_percentage: float = field(init=False)

    def to_dict(self) -> dict:
        return {
            "original_size": self.original_size,
            "optimized_size": self.optimized_size,
            "reduction_bytes": self.reduction_bytes,
            "reduction_percentage": self.reduction_percentage,
            "warnings": self.warnings,
            "errors": self.errors,
        }
    def __post_init__(self) -> None:
        """
        Calculate reduction metrics automatically after initialization.

        This method computes:
        - reduction_bytes: The absolute difference between original and optimized sizes
        - reduction_percentage: The percentage of size reduction (handles division by zero)
        """
        self.reduction_bytes = self.original_size - self.optimized_size
        if self.original_size > 0:
            self.reduction_percentage = (self.reduction_bytes / self.original_size) * 100
        else:
            self.reduction_percentage = 0.0


class Optimizer(ABC):
    """
    Abstract base class for document optimizers in the plugin architecture.

    This class defines the interface that all optimizer implementations must follow.
    Optimizers are responsible for reducing file sizes while maintaining quality
    standards. The architecture supports:

    - Plugin-based optimization (extend by creating new subclasses)
    - Flexible file handling (beyond just extension matching)
    - Configurable optimization behavior
    - Detailed result tracking with warnings and errors

    Subclasses must implement all abstract methods and properties to provide
    concrete optimization functionality.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the name of this optimizer.

        Should be a human-readable identifier suitable for logging and UI display.

        Returns:
            A descriptive name for the optimizer (e.g., "PDF Optimizer", "Office Document Optimizer").
        """
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """
        Return the list of file extensions this optimizer supports.

        Extensions should include the leading dot and be lowercase for consistency.
        These are used as hints for router implementations but are not the only
        way files are matched to optimizers.

        Returns:
            A list of file extensions (e.g., [".pdf", ".PDF"] or [".docx", ".doc"]).
        """
        pass

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """
        Check if this optimizer can handle the given file.

        This method allows for flexible handling beyond just extension matching.
        Implementations may check file headers (magic numbers), content inspection,
        or other properties to determine suitability.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if this optimizer can handle the file, False otherwise.
        """
        pass

    @abstractmethod
    def optimize(self, file_path: Path, config: Mapping[str, Any]) -> OptimizationResult:
        """
        Optimize the given file according to the provided configuration.

        This is the main entry point for optimization. Implementations should:
        1. Validate the input file exists and is accessible
        2. Read and process the file according to the configuration
        3. Write the optimized output
        4. Return detailed results with metrics

        Args:
            file_path: Path to the file to optimize.
            config: Configuration dictionary for this optimizer.
                    The structure and contents depend on the specific optimizer
                    implementation. May contain keys like:
                    - compression_level: Aggressiveness of compression
                    - quality_threshold: Acceptable quality loss
                    - preserve_metadata: Whether to keep original metadata
                    - And any other optimizer-specific options

        Returns:
            An OptimizationResult containing size information, metrics, and any
            warnings or errors encountered during optimization.

        Raises:
            FileNotFoundError: If the file does not exist or is not readable.
            ValueError: If the file is not supported by this optimizer or if
                       the configuration is invalid.
            IOError: If there are file system access issues.
            Exception: Subclasses may raise additional specific exceptions for
                      optimization-specific errors.
        """
        pass
