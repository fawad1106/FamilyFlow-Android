from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="LifeOS", version="0.1.0")

app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

@app.get("/")
async def home():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "project": "life-os"}
