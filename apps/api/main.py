"""
DeSynth FastAPI Application.
High-Performance HTTP REST & Stream API for AI Watermark Removal and Forensic Verification.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
import io
import cv2
import numpy as np

from core.pipeline import DeSynthPipeline
from core.detector_oracle import DetectorOracle
from core.c2pa_stripper import C2PAStripper

app = FastAPI(
    title="DeSynth Engine API",
    description="Cryptographic and Multi-Spectral AI Watermark (SynthID, Tree-Ring) Neutralization Service",
    version="2.0.0",
)

# Enable CORS for Next.js web studio & third-party integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "DeSynth AI Watermark Neutralization Engine",
        "version": "2.0.0",
        "stack": "FastAPI + NumPy + SciPy + OpenCV",
    }


@app.get("/api/presets")
def list_presets():
    return {
        "presets": DeSynthPipeline.PRESETS,
        "default": "balanced",
    }


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Inspects image for SynthID, Fourier harmonic artifacts, kurtosis anomalies, and C2PA metadata.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    meta = C2PAStripper.inspect_metadata(content)
    img_bgr = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Invalid image format.")

    forensics = DetectorOracle.evaluate(img_bgr, has_c2pa=meta["has_ai_metadata"])

    return {
        "filename": file.filename,
        "byte_size": len(content),
        "resolution": {"width": img_bgr.shape[1], "height": img_bgr.shape[0]},
        "forensics": forensics,
        "metadata": meta,
    }


@app.post("/api/purify")
async def purify_image(
    file: UploadFile = File(...),
    preset: str = Form("balanced"),
    format: str = Form("PNG"),
    quality: int = Form(96),
):
    """
    Executes full multi-stage watermark neutralization and returns purified image.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        pipeline = DeSynthPipeline(preset=preset)
        result = pipeline.process_bytes(content, output_format=format, output_quality=quality)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    mime_type = "image/png" if format.upper() == "PNG" else "image/jpeg"

    # Return clean image with forensic headers
    headers = {
        "X-DeSynth-Time-Ms": str(result["elapsed_ms"]),
        "X-DeSynth-Preset": result["preset"],
        "X-DeSynth-PSNR": str(result["quality"]["psnr_db"]),
        "X-DeSynth-SSIM": str(result["quality"]["ssim"]),
        "X-DeSynth-Risk-Reduction": str(result["forensics"]["risk_reduction_percent"]),
        "X-DeSynth-C2PA-Stripped": str(result["metadata_sanitized"]),
        "Access-Control-Expose-Headers": "*",
    }

    return Response(content=result["clean_bytes"], media_type=mime_type, headers=headers)


@app.post("/api/purify/inspect")
async def purify_and_inspect(
    file: UploadFile = File(...),
    preset: str = Form("balanced"),
    format: str = Form("PNG"),
    quality: int = Form(96),
):
    """
    Purifies image and returns full before/after JSON report along with base64 data URLs.
    """
    import base64

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    pipeline = DeSynthPipeline(preset=preset)
    result = pipeline.process_bytes(content, output_format=format, output_quality=quality)

    mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
    b64_clean = base64.b64encode(result["clean_bytes"]).decode("utf-8")
    b64_orig = base64.b64encode(content).decode("utf-8")

    response_data = {
        "filename": file.filename,
        "elapsed_ms": result["elapsed_ms"],
        "preset": result["preset"],
        "quality": result["quality"],
        "forensics": result["forensics"],
        "metadata_sanitized": result["metadata_sanitized"],
        "stripped_signatures": result["stripped_signatures"],
        "images": {
            "original_data_url": f"data:{mime};base64,{b64_orig}",
            "purified_data_url": f"data:{mime};base64,{b64_clean}",
        },
    }

    return JSONResponse(content=response_data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
