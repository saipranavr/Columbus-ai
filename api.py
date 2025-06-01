from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import re
from text_to_video import TextToVideo
from gemini_fetch import generate_final_script, discover_videos_and_initial_info, generate_detailed_summaries
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
    """
    Removes all text within square brackets and the brackets themselves.
    Also cleans up any resulting double spaces or empty lines.
    """
    # Remove text within square brackets
    cleaned = re.sub(r'\[.*?\]', '', script)
    
    # Clean up double spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Clean up empty lines
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

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
        
        # Clean the script by removing bracketed text
        cleaned_script = clean_script(final_script)
        print("📝 Cleaned script:", cleaned_script)
        
        # Create mapping between cleaned script positions and bracketed text
        script_mapping = create_script_mapping(final_script, cleaned_script)
        print("🗺️ Script mapping:", script_mapping)
        
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
        
        return VideoResponse(
            status="success",
            video_url=result['video']['url'],
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