import os
import shutil
from fastapi import FastAPI, UploadFile, File

app = FastAPI(title="Cloud Ingestion Receiver")
UPLOAD_DIR = "/app/cloud_data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload-parquet")
async def upload_parquet(file: UploadFile = File(...)):
    dest_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    size_kb = os.path.getsize(dest_path) / 1024.0
    print(f"[*] Nhận thành công file Parquet: {file.filename} ({size_kb:.2f} KB)")
    return {"status": "success", "file": file.filename, "size_kb": size_kb}

@app.get("/")
def health():
    return {"status": "Cloud Receiver is running"}
