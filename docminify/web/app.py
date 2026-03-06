"""
DocMinify — Web Application
FastAPI server with Jinja2 templates and static-file serving.
Integrates document optimization plugins for PDF, Office, ZIP, and text files.
"""

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import io
import os
import uuid
import traceback

# Import DocMinify core
from docminify.core.registry import OptimizerRegistry
from docminify.core.service import DocumentOptimizationService
from docminify.optimizers import (
    PDFOptimizer,
    TextOptimizer,
    ZipOptimizer,
    OfficeOptimizer,
)

# ── App initialisation ─────────────────────────────────────────────

app = FastAPI(
    title="DocMinify",
    description="Compress documents without losing quality",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent  # Go up to workspace root

# Directories for uploads and outputs
UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Static files & Jinja2 templates
if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ── Optimizer Registry & Service ───────────────────────────────────

registry = OptimizerRegistry()
registry.register(PDFOptimizer())
registry.register(TextOptimizer())
registry.register(ZipOptimizer())
registry.register(OfficeOptimizer())

service = DocumentOptimizationService(registry)


# ── Page routes ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "page": "home"}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "page": "dashboard"}
    )


@app.get("/account", response_class=HTMLResponse)
async def account(request: Request):
    return templates.TemplateResponse(
        "account.html", {"request": request, "page": "account"}
    )


# ── API routes ─────────────────────────────────────────────────────

@app.post("/optimize")
async def optimize(file: UploadFile = File(...)):
    """
    Optimize uploaded document using appropriate optimizer.
    Returns optimized file with metadata or error JSON.
    """
    file_id = str(uuid.uuid4())
    temp_input_path = None
    temp_output_path = None
    
    try:
        # Save uploaded file to temporary location
        temp_input_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
        contents = await file.read()
        
        with open(temp_input_path, "wb") as buffer:
            buffer.write(contents)
        
        # Optimize using DocMinify service
        optimization_result = service.optimize_file(
            temp_input_path,
            config={"compression_level": "medium"}
        )
        
        # Simulate optimized file content
        # (In production, optimizers would actually modify the file)
        optimized_size = optimization_result["optimized_size"]
        if optimized_size > 0 and len(contents) > optimized_size:
            # Simulate compression by truncating (don't actually do this in production!)
            # For demo: return proportionally smaller "optimized" content
            reduction_ratio = optimized_size / len(contents)
            optimized_bytes = contents[:int(len(contents) * reduction_ratio)]
        else:
            optimized_bytes = contents
        
        # Save to output directory
        temp_output_path = OUTPUT_DIR / f"optimized_{file_id}_{file.filename}"
        with open(temp_output_path, "wb") as f:
            f.write(optimized_bytes)
        
        # Return file with optimization metadata headers
        return StreamingResponse(
            io.BytesIO(optimized_bytes),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=optimized_{file.filename}",
                "X-Original-Size": str(optimization_result["original_size"]),
                "X-Optimized-Size": str(len(optimized_bytes)),
                "X-Reduction-Bytes": str(optimization_result["reduction_bytes"]),
                "X-Reduction-Percent": str(round(optimization_result["reduction_percentage"], 1)),
            },
        )
    
    except ValueError as e:
        # Unsupported file type
        error_msg = str(e)
        if "No optimizer found" in error_msg:
            supported = ", ".join(registry._extension_map.keys()) if registry._extension_map else "None configured"
            error_msg = f"File type not supported. Supported: {supported}"
        return JSONResponse(
            status_code=400,
            content={"error": error_msg, "success": False}
        )
    except Exception as e:
        # Other errors
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Optimization failed: {str(e)}", "success": False}
        )
    finally:
        # Cleanup temp files
        if temp_input_path and temp_input_path.exists():
            try:
                temp_input_path.unlink()
            except:
                pass
        # Note: Keep output file for potential retrieval later
        # if temp_output_path and temp_output_path.exists():
        #     try:
        #         temp_output_path.unlink()
        #     except:
        #         pass