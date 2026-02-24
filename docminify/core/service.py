"""
Document optimization service for the docminify tool.

This module provides the main service interface for optimizing documents,
coordinating between the registry and optimizer plugins.
"""

from pathlib import Path
from typing import Mapping, Any

from docminify.core.registry import OptimizerRegistry
from docminify.optimizers.base import OptimizationResult


class DocumentOptimizationService:
    """
    Service for optimizing documents using registered optimizers.

    This class provides the main entry point for document optimization operations.
    It handles file validation, optimizer selection, and error management while
    keeping the implementation clean and testable.

    Design principles:
    - Dependency injection: Receives registry as constructor parameter
    - Single responsibility: Coordinates optimization, doesn't perform it
    - No side effects: Pure function behavior (except file I/O)
    - Type-safe: Full type hints with modern Python typing
    - Testable: Simple interface, easy to mock dependencies

    Example:
        >>> registry = OptimizerRegistry()
        >>> registry.register(pdf_optimizer)
        >>> service = DocumentOptimizationService(registry)
        >>> result = service.optimize_file(Path("document.pdf"))
        >>> print(result["reduction_percentage"])
    """

    def __init__(self, registry: OptimizerRegistry) -> None:
        """
        Initialize the optimization service with a registry.

        Args:
            registry: An OptimizerRegistry instance containing registered optimizers.
        """
        self._registry = registry

    def optimize_file(
        self,
        file_path: Path,
        config: Mapping[str, Any] | None = None,
    ) -> dict:
        """
        Optimize a document file using the appropriate registered optimizer.

        This method performs the following steps:
        1. Validates that the file exists and is accessible
        2. Queries the registry to find a suitable optimizer
        3. Raises ValueError if no optimizer can handle the file
        4. Invokes the optimizer with the provided configuration
        5. Converts the OptimizationResult to a dictionary

        Args:
            file_path: Path to the file to optimize.
            config: Optional configuration dictionary for the optimizer.
                   If None, an empty dictionary will be used.
                   The structure depends on the specific optimizer implementation.

        Returns:
            A dictionary containing optimization results with keys:
            - original_size (int): Original file size in bytes
            - optimized_size (int): Optimized file size in bytes
            - reduction_bytes (int): Bytes saved by optimization
            - reduction_percentage (float): Percentage reduction
            - warnings (list): Non-fatal warnings from optimization
            - errors (list): Errors encountered during optimization

        Raises:
            FileNotFoundError: If the file does not exist or is not accessible.
            ValueError: If no registered optimizer can handle the file.
            Exception: Any exception raised by the optimizer during optimization.

        Example:
            >>> service = DocumentOptimizationService(registry)
            >>> result = service.optimize_file(Path("file.pdf"))
            >>> print(f"Saved {result['reduction_bytes']} bytes")
            >>> result = service.optimize_file(
            ...     Path("file.pdf"),
            ...     config={"compression_level": "high"}
            ... )
        """
        # Normalize to Path object if needed
        file_path = Path(file_path)

        # Validate file exists and is accessible
        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Path is not a file: {file_path}"
            )

        # Find appropriate optimizer
        optimizer = self._registry.find_for_file(file_path)
        if optimizer is None:
            raise ValueError(
                f"No optimizer found for file: {file_path}. "
                f"Registered optimizers support: "
                f"{self._get_supported_extensions_summary()}"
            )

        # Use empty config if none provided
        optimization_config = config or {}

        # Perform optimization
        result: OptimizationResult = optimizer.optimize(file_path, optimization_config)

        # Convert result to dictionary
        return self._result_to_dict(result)

    def _get_supported_extensions_summary(self) -> str:
        """
        Generate a human-readable summary of supported extensions.

        Returns:
            A string describing all supported extensions across all optimizers.
        """
        all_extensions = set()
        for optimizer in self._registry.get_all():
            all_extensions.update(optimizer.supported_extensions)

        if all_extensions:
            return ", ".join(sorted(all_extensions))
        return "none configured"

    @staticmethod
    def _result_to_dict(result: OptimizationResult) -> dict:
        """
        Convert an OptimizationResult dataclass to a dictionary.

        Args:
            result: The OptimizationResult to convert.

        Returns:
            A dictionary representation of the result.
        """
        return {
            "original_size": result.original_size,
            "optimized_size": result.optimized_size,
            "reduction_bytes": result.reduction_bytes,
            "reduction_percentage": result.reduction_percentage,
            "warnings": result.warnings,
            "errors": result.errors,
        }
