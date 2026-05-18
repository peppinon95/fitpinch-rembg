import os
import asyncio
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import Response
from rembg import remove, new_session
from PIL import Image

app = FastAPI()

API_KEY = os.getenv("BG_REMOVE_API_KEY", "").strip()

REMOVE_BG_CONCURRENCY = int(os.getenv("REMOVE_BG_CONCURRENCY", "1"))
QUEUE_TIMEOUT_SECONDS = int(os.getenv("QUEUE_TIMEOUT_SECONDS", "180"))

queue = asyncio.Semaphore(REMOVE_BG_CONCURRENCY)
SESSION = new_session("u2netp")


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

    try:
        await asyncio.wait_for(queue.acquire(), timeout=QUEUE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=429,
            detail="Server busy. Try again shortly.",
        )

    try:
        output_bytes = await asyncio.to_thread(
            remove,
            input_bytes,
            session=SESSION,
        )

        image = Image.open(BytesIO(output_bytes)).convert("RGBA")

        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)

        padding = 32
        canvas = Image.new(
            "RGBA",
            (image.width + padding * 2, image.height + padding * 2),
            (0, 0, 0, 0),
        )
        canvas.paste(image, (padding, padding), image)
        image = canvas

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        queue.release()
