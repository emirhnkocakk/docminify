"""
Optimizer registry for managing plugin-based document optimizers.

This module provides a centralized registry for optimizer instances, handling
registration, lookup, and routing of files to appropriate optimizers.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set

from docminify.optimizers.base import Optimizer


class OptimizerRegistry:
    """
    Registry for managing optimizer instances in a plugin-based architecture.

    This class provides a centralized mechanism for:
    - Registering optimizer instances
    - Preventing duplicate registrations
    - Mapping file extensions to optimizers
    - Finding the appropriate optimizer for a given file

    The registry normalizes all extensions to lowercase for consistent matching
    and supports flexible file routing through both extension lookup and the
    optimizer's can_handle() method.

    Design principles:
    - No global state: Each registry is an independent instance
    - Type-safe: Uses type hints throughout
    - Testable: Simple, deterministic behavior
    - Extensible: Easy to add new lookup strategies
    """

    def __init__(self) -> None:
        """
        Initialize a new optimizer registry.

        The registry maintains:
        - _optimizers: List of registered optimizer instances
        - _extension_map: Mapping of extensions to optimizer lists
        - _optimizer_names: Set of registered optimizer names for uniqueness checks
        """
        self._optimizers: List[Optimizer] = []
        self._extension_map: Dict[str, List[Optimizer]] = {}
        self._optimizer_names: Set[str] = set()

    def register(self, optimizer: Optimizer) -> None:
        """
        Register an optimizer instance.

        An optimizer can only be registered once. Attempting to register an
        optimizer with a name that already exists will raise a ValueError.

        The optimizer's supported extensions are extracted, normalized to
        lowercase, and added to the extension map for efficient routing.

        Args:
            optimizer: An instance of Optimizer (or subclass) to register.

        Raises:
            ValueError: If an optimizer with the same name is already registered.

        Example:
            >>> registry = OptimizerRegistry()
            >>> registry.register(pdf_optimizer)
            >>> registry.register(pdf_optimizer)  # Raises ValueError
        """
        optimizer_name = optimizer.name

        if optimizer_name in self._optimizer_names:
            raise ValueError(
                f"Optimizer '{optimizer_name}' is already registered. "
                f"Each optimizer must have a unique name."
            )

        # Register the optimizer
        self._optimizers.append(optimizer)
        self._optimizer_names.add(optimizer_name)

        # Index supported extensions (normalized to lowercase)
        for ext in optimizer.supported_extensions:
            normalized_ext = ext.lower()
            if normalized_ext not in self._extension_map:
                self._extension_map[normalized_ext] = []
            self._extension_map[normalized_ext].append(optimizer)

    def get_all(self) -> List[Optimizer]:
        """
        Retrieve all registered optimizers.

        Returns:
            A list of all registered optimizer instances, in registration order.
        """
        return self._optimizers.copy()

    def find_by_extension(self, extension: str) -> List[Optimizer]:
        """
        Find optimizers that support a specific file extension.

        Extensions are normalized to lowercase before lookup.

        Args:
            extension: The file extension to search for (e.g., ".pdf", ".PDF").

        Returns:
            A list of optimizers supporting this extension, in registration order.
            Returns an empty list if no optimizers support the extension.

        Example:
            >>> registry = OptimizerRegistry()
            >>> registry.register(pdf_optimizer)
            >>> registry.register(pdf_optimizer_v2)
            >>> optimizers = registry.find_by_extension(".pdf")
            >>> len(optimizers)
            2
        """
        normalized_ext = extension.lower()
        return self._extension_map.get(normalized_ext, []).copy()

    def find_for_file(self, file_path: Path) -> Optional[Optimizer]:
        """
        Find the first optimizer that can handle the given file.

        The routing strategy is:
        1. Extract the file extension (normalized to lowercase)
        2. Look up optimizers supporting this extension
        3. If multiple candidates exist, test each with can_handle()
        4. If no extension match found, test all optimizers with can_handle()
        5. Return the first optimizer that claims it can handle the file

        This two-phase approach optimizes common cases (extension matches) while
        supporting flexible handling (via can_handle()) for ambiguous or special files.

        Args:
            file_path: Path to the file to find an optimizer for.

        Returns:
            The first optimizer that can handle the file, or None if no optimizer
            can handle it.

        Example:
            >>> registry = OptimizerRegistry()
            >>> registry.register(pdf_optimizer)
            >>> registry.register(fallback_optimizer)
            >>> optimizer = registry.find_for_file(Path("document.pdf"))
            >>> if optimizer:
            ...     result = optimizer.optimize(Path("document.pdf"), config={})
        """
        file_ext = file_path.suffix.lower()

        # Phase 1: Try extension-based lookup first
        candidates = self.find_by_extension(file_ext)
        for optimizer in candidates:
            if optimizer.can_handle(file_path):
                return optimizer

        # Phase 2: If no extension match, try all optimizers
        # (useful for files with wrong extensions or content-based matching)
        for optimizer in self._optimizers:
            if optimizer.can_handle(file_path):
                return optimizer

        return None
