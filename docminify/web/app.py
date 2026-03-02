from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import shutil
import os
import uuid

from docminify.core.registry import OptimizerRegistry
from docminify.core.service import DocumentOptimizationService
from docminify.optimizers.pdf_optimizer import PDFOptimizer

app = FastAPI()
templates = Jinja2Templates(directory="docminify/web/templates")

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Registry setup
registry = OptimizerRegistry()
registry.register(PDFOptimizer())

service = DocumentOptimizationService(registry)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/optimize")
async def optimize_file(request: Request, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    output_path = os.path.join(OUTPUT_DIR, f"optimized_{file_id}_{file.filename}")

    # Save uploaded file
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Optimize
    result = service.optimize_file(input_path)

    # Eğer optimizer dosya üretiyorsa output_path'e yazmalı
    # Şimdilik aynı dosyayı kopyalayalım (gerçek optimize fonksiyonuna göre değişebilir)
    shutil.copy(input_path, output_path)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": result,
            "download_link": f"/download/{os.path.basename(output_path)}",
        },
    )


@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    return FileResponse(file_path, filename=filename)