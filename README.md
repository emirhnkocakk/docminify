# DocMinify

A plugin-based document optimization framework built in Python.

## Features

- Plugin-based optimizer architecture
- Registry-driven routing
- Clean service layer
- Extensible design
- Production-ready structure

## Current Optimizers

- PDF Optimizer (simulated compression)

## Architecture
docminify/
core/
registry.py
service.py
optimizers/
base.py
pdf_optimizer.py


## Example Usage

```python
from pathlib import Path
from docminify.core.registry import OptimizerRegistry
from docminify.core.service import DocumentOptimizationService
from docminify.optimizers.pdf_optimizer import PdfOptimizer

registry = OptimizerRegistry()
registry.register(PdfOptimizer())

service = DocumentOptimizationService(registry)

result = service.optimize_file(Path("sample.pdf"))
print(result)

Roadmap

 Real PDF compression integration

 Image optimizer

 CLI support

 Packaging for PyPI

 Full test coverage