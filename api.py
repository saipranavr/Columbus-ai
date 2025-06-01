from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import re
import os
import requests
from text_to_video import TextToVideo
from gemini_fetch import generate_final_script, discover_videos_and_initial_info, generate_detailed_summaries
from video_search import create_video_url_mapping
from video_inserter import VideoInserter
from typing import Optional, Dict, List, Tuple

app = FastAPI(title="Travel Video Generator API")

def create_script_mapping(original_script: str, cleaned_script: str) -> Dict[int, str]:
    """
    Creates a mapping between positions in the cleaned script and their corresponding bracketed text
    from the original script.
    
    Args:
        original_script: The original script with bracketed text
        cleaned_script: The cleaned script without bracketed text
        
    Returns:
        A dictionary where:
        - Keys are the positions (word indices) in the cleaned script
        - Values are the bracketed text from the original script
    """
    # Split both scripts into words
    original_words = original_script.split()
    cleaned_words = cleaned_script.split()
    
    # Initialize mapping
    mapping: Dict[int, str] = {}
    
    # Track positions in both scripts
    orig_pos = 0
    clean_pos = 0
    
    while orig_pos < len(original_words):
        word = original_words[orig_pos]
        
        # Check if this word contains the start of a bracket
        if '[' in word:
            # Find the complete bracketed text
            bracket_text = ''
            temp_pos = orig_pos
            while temp_pos < len(original_words):
                current_word = original_words[temp_pos]
                bracket_text += current_word + ' '
                if ']' in current_word:
                    break
                temp_pos += 1
            
            # Store the mapping
            mapping[clean_pos] = bracket_text.strip()
            
            # Skip all words that were part of the bracketed text
            orig_pos = temp_pos + 1
        else:
            # If this word is not part of a bracket, increment both positions
            orig_pos += 1
            clean_pos += 1
    
    return mapping

def clean_script(script: str) -> str:
    """Remove bracketed text from the script."""
    return re.sub(r'\[.*?\]', '', script)

def download_video(url: str, output_path: str) -> str:
    """Download a video from a URL and save it locally, or copy a local file."""
    try:
        # If it's a local file path (starts with / or .)
        if url.startswith('/') or url.startswith('./'):
            # Just copy the file
            import shutil
            shutil.copy2(url, output_path)
            return f"file://{os.path.abspath(output_path)}"
        
        # Otherwise treat as URL
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return f"file://{os.path.abspath(output_path)}"
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        raise

class VideoRequest(BaseModel):
    city_name: str
    local_language: Optional[str] = None

class VideoResponse(BaseModel):
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None
    script_mapping: Optional[Dict[int, str]] = None

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
            
        # TESTING: Trim script to 25 words
        words = final_script.split()
        final_script = ' '.join(words[:100])
        print("📝 TESTING: Trimmed script to 25 words:", final_script)
        
        # Clean the script by removing bracketed text
        cleaned_script = clean_script(final_script)
        print("📝 Cleaned script:", cleaned_script)
        
        # Create mapping between cleaned script positions and bracketed text
        script_mapping = create_script_mapping(final_script, cleaned_script)
        print("🗺️ Script mapping:", script_mapping)
        print("📝 Original script with brackets:", final_script)
        print("📝 Cleaned script:", cleaned_script)
        
        # Step 2: Generate video from the script
        print("🎥 Generating video from script...")
        ttv = TextToVideo()
        
        def status_callback(status: str):
            print(f"🔄 Video Status: {status}")
        
        # Generate video asynchronously
        result = await ttv.generate_video_async(
            text=cleaned_script,
            avatar_id="emily_primary",
            on_status_update=status_callback
        )
        
        # Step 3: Download the talking head video
        print("📥 Downloading talking head video...")
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        talking_head_path = os.path.join(output_dir, "talking_head.mp4")
        talking_head_url = download_video(result['video']['url'], talking_head_path)
        print(f"✅ Talking head video downloaded to: {talking_head_url}")
        
        # Step 4: Create video URL mapping
        print("🔍 Creating video URL mapping...")
        video_url_mapping = create_video_url_mapping(script_mapping)
        print("🗺️ Video URL mapping:", video_url_mapping)
        
        # Step 5: Prepare videos for insertion
        print("📥 Preparing videos for insertion...")
        video_timestamps = []
        for position, local_path in video_url_mapping.items():
            if local_path:
                # Calculate timestamp (roughly 1 word per second)
                timestamp = position * 1.0
                print(f"⏱️ Position {position} -> Timestamp {timestamp}s -> Path: {local_path}")
                
                # Convert local path to file:// URL
                file_url = f"file://{os.path.abspath(local_path)}"
                video_timestamps.append((file_url, timestamp))
        
        print("🎯 Final video timestamps:", video_timestamps)
        
        # Step 6: Insert videos
        print("🎬 Inserting videos...")
        inserter = VideoInserter()
        final_output_path = os.path.join(output_dir, "final_video.mp4")
        
        result_path = inserter.insert_multiple_videos(
            main_video_path=talking_head_url,
            video_timestamps=video_timestamps,
            output_path=final_output_path
        )
        
        return VideoResponse(
            status="success",
            video_url=f"file://{os.path.abspath(result_path)}",
            script_mapping=script_mapping
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