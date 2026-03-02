from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import os
import uuid
import traceback

from docminify.core.registry import OptimizerRegistry
from docminify.core.service import DocumentOptimizationService
from docminify.optimizers import (
    PDFOptimizer,
    TextOptimizer,
    ZipOptimizer,
    OfficeOptimizer,
)

app = FastAPI()
templates = Jinja2Templates(directory="docminify/web/templates")

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Registry setup - Tüm optimizerleri kaydet
registry = OptimizerRegistry()
registry.register(PDFOptimizer())
registry.register(TextOptimizer())
registry.register(ZipOptimizer())
registry.register(OfficeOptimizer())

service = DocumentOptimizationService(registry)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/optimize")
async def optimize_file(request: Request, file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        output_path = os.path.join(OUTPUT_DIR, f"optimized_{file_id}_{file.filename}")

        # Save uploaded file
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Optimize - Path objesine dönüştür
        result = service.optimize_file(Path(input_path))

        # Optimize edilmiş dosyayı kopyala
        shutil.copy(input_path, output_path)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": result,
                "download_link": f"/download/{os.path.basename(output_path)}",
                "success": True,
            },
        )
    except ValueError as e:
        # Desteklenmeyen dosya türü
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": f"Desteklenmeyen dosya türü: {str(e)}",
                "success": False,
            },
        )
    except Exception as e:
        # Diğer hatalar
        error_msg = f"Optimizasyon sırasında hata: {str(e)}"
        traceback.print_exc()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": error_msg,
                "success": False,
            },
        )


@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    return FileResponse(file_path, filename=filename)