
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from rembg import remove

app = FastAPI()

@app.post("/remove-bg")
async def remove_bg(file: UploadFile = File(...)):
    input_bytes = await file.read()
    output_bytes = remove(input_bytes)

    return Response(
        content=output_bytes,
        media_type="image/png",
    )




