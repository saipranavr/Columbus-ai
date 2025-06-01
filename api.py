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
from moviepy.editor import VideoFileClip

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
        # TESTING: Use hardcoded script
        final_script = """Hey globetrotters! Welcome back to the channel! Today, we're diving headfirst into one of the world's most iconic cities: London! [Show vibrant montage of London landmarks] Get ready for a whirlwind tour packed with famous sights, delicious food, and some seriously cool hidden gems. First up, the must-see landmarks. [Show footage of Buckingham Palace] Buckingham Palace, of course! Did you know that the State Rooms, where the Queen would receive guests, are only open to the public during the summer months? Definitely worth a visit if you're planning a summer trip. [Show footage of Houses of Parliament and Big Ben]"""
        print("📝 Using test script:", final_script)
        
        # Clean the script by removing bracketed text
        cleaned_script = clean_script(final_script)
        print("📝 Cleaned script:", cleaned_script)
        
        # Create mapping between cleaned script positions and bracketed text
        script_mapping = create_script_mapping(final_script, cleaned_script)
        print("🗺️ Script mapping:", script_mapping)
        
        # TESTING: Use existing talking head video
        print("🎥 Using existing talking head video...")
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        talking_head_path = os.path.join(output_dir, "talking_head.mp4")
        talking_head_url = f"file://{os.path.abspath(talking_head_path)}"
        print(f"✅ Using talking head video at: {talking_head_url}")
        
        # Get talking head video duration
        main_video = VideoFileClip(talking_head_path)
        video_duration = main_video.duration
        main_video.close()
        print(f"⏱️ Talking head video duration: {video_duration}s")
        
        # Step 4: Create video URL mapping
        print("🔍 Creating video URL mapping...")
        video_url_mapping = create_video_url_mapping(script_mapping)
        print("🗺️ Video URL mapping:", video_url_mapping)
        
        # Step 5: Prepare videos for insertion
        print("📥 Preparing videos for insertion...")
        video_timestamps = []
        
        # Calculate total words in cleaned script
        total_words = len(cleaned_script.split())
        print(f"📝 Total words in script: {total_words}")
        
        for position, local_path in video_url_mapping.items():
            if local_path:
                # Calculate timestamp based on word position and video duration
                # Distribute timestamps evenly across the video duration
                timestamp = (position / total_words) * video_duration
                print(f"⏱️ Position {position}/{total_words} -> Timestamp {timestamp:.2f}s -> Path: {local_path}")
                
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