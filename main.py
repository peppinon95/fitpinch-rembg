import os
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import Response
from rembg import remove
from PIL import Image

app = FastAPI()

API_KEY = os.getenv("BG_REMOVE_API_KEY", "").strip()


@app.get("/")
async def root():
    return {"ok": True, "service": "fitpinch-rembg"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/remove-bg")
async def remove_bg(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    input_bytes = await file.read()

    if not input_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(input_bytes) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large")

    output_bytes = remove(input_bytes)

    image = Image.open(BytesIO(output_bytes)).convert("RGBA")

    max_side = 1280
    w, h = image.size

    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        image = image.resize(
            (int(w * ratio), int(h * ratio)),
            Image.LANCZOS,
        )

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)

    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
    )
