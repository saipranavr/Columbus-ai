from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from text_to_video import TextToVideo
from gemini_fetch import generate_final_script, discover_videos_and_initial_info, generate_detailed_summaries
from typing import Optional

app = FastAPI(title="Travel Video Generator API")

class VideoRequest(BaseModel):
    city_name: str
    local_language: Optional[str] = None

class VideoResponse(BaseModel):
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None

@app.post("/generate-video", response_model=VideoResponse)
async def generate_video(request: VideoRequest):
    try:
        # Step 1: Generate the travel script
        print(f"📝 Generating travel script for {request.city_name}...")
        
        # Get video information
        discovered_video_info = discover_videos_and_initial_info(
            request.city_name,
            request.local_language or "English"
        )
        
        if not discovered_video_info:
            raise HTTPException(
                status_code=400,
                detail=f"Could not find video information for {request.city_name}"
            )
        
        # Generate detailed summaries
        detailed_summaries = generate_detailed_summaries(
            discovered_video_info,
            request.city_name,
            request.local_language or "English"
        )
        
        if not detailed_summaries:
            raise HTTPException(
                status_code=400,
                detail=f"Could not generate summaries for {request.city_name}"
            )
        
        # Generate final script
        final_script = generate_final_script(detailed_summaries, request.city_name)
        
        if not final_script:
            raise HTTPException(
                status_code=400,
                detail=f"Could not generate final script for {request.city_name}"
            )
        
        # Step 2: Generate video from the script
        print("🎥 Generating video from script...")
        ttv = TextToVideo()
        
        def status_callback(status: str):
            print(f"🔄 Video Status: {status}")
        
        # Generate video asynchronously
        result = await ttv.generate_video_async(
            text=final_script,
            avatar_id="emily_primary",
            on_status_update=status_callback
        )
        
        return VideoResponse(
            status="success",
            video_url=result['video']['url']
        )
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return VideoResponse(
            status="error",
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 