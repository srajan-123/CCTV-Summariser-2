import os
import shutil
import uuid
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from processing import process_video
from config import OUTPUT_DIR

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-video")
async def process_video_endpoint(file: UploadFile = File(...)):
    try:
        input_filename = os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex}_{file.filename}")
        with open(input_filename, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        logs, summary_path = process_video(input_filename)
        os.remove(input_filename)
        
        # here the summary_video is the path of local video file where it is stored and frontend can use this path to download the video
        return JSONResponse(content={
            "logs": logs,
            "summary_video": summary_path
        })
    except Exception as e:
        logging.error(f"Error processing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-video")
async def download_video(video_path: str):
    if os.path.exists(video_path):
        return FileResponse(video_path, media_type='video/mp4', filename="summary.mp4")
    else:
        raise HTTPException(status_code=404, detail="Video not found")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
