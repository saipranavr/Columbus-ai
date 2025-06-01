import os
import sieve
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def approximate_word_time(full_script_text: str, target_word_index: int, total_video_duration_seconds: float) -> float:
    """
    Approximates when a word will be spoken in the video based on its position in the script.
    
    Args:
        full_script_text: The complete script text
        target_word_index: Index of the word in the script
        total_video_duration_seconds: Total duration of the video in seconds
        
    Returns:
        Approximate time in seconds when the word will be spoken
    """
    words = full_script_text.split()  # Simple word tokenization
    total_words_in_script = len(words)

    if total_words_in_script == 0:
        return 0  # Or raise error
    if target_word_index >= total_words_in_script:
        raise ValueError("Target word index is out of bounds.")

    # target_word_index is how many words have been spoken BEFORE the word we're interested in
    proportion_spoken = target_word_index / total_words_in_script
    approx_time = proportion_spoken * total_video_duration_seconds
    return approx_time

def search_video_url(text: str) -> Optional[Any]:
    """
    Search for a relevant video URL using Sieve Scout Search.
    
    Args:
        text: The text to search for
        
    Returns:
        The first matching video result or None if no matches found
    """
    try:
        # Get the scout-search function
        scout_search = sieve.function.get("sieve/scout-search")
        
        # Run the search with specified parameters
        output = scout_search.push(
            query=text,
            num_results=1,
            format_results="raw_video_480p",
            min_relevance_score=0.7,
            aspect_ratio=[],
            only_creative_commons=False,
            exclude_black_bar=True,
            exclude_static=True,
            exclude_overlay=True,
            min_quality_score=0.8,
            max_quality_score=1,
            min_video_width=0,
            max_video_width=-1,
            min_video_height=0,
            max_video_height=-1,
            min_motion_score=0,
            max_motion_score=1,
            min_duration=3,
            max_duration=-1
        )
        
        # Get the first result
        for result in output.result():
            return result
        
        return None
        
    except Exception as e:
        print(f"❌ Error searching for video: {str(e)}")
        return None

def create_video_url_mapping(script_mapping: Dict[int, str]) -> Dict[int, str]:
    """
    Creates a mapping of script positions to video URLs using Sieve search.
    
    Args:
        script_mapping: Dictionary mapping script positions to bracketed text
        
    Returns:
        Dictionary mapping script positions to video URLs
    """
    video_url_mapping = {}
    
    for position, bracketed_text in script_mapping.items():
        print(f"🔍 Searching for video for position {position}: {bracketed_text}")
        
        try:
            # Remove brackets and clean the text
            search_text = bracketed_text.strip('[]')
            
            # Search for video
            result = search_video_url(search_text)
            
            if result and hasattr(result[0], 'path'):
                video_url_mapping[position] = result[0].path
                print(f"✅ Found video URL for position {position}")
            else:
                print(f"⚠️ No video found for position {position}")
                video_url_mapping[position] = None
                
        except Exception as e:
            print(f"❌ Error processing position {position}: {str(e)}")
            video_url_mapping[position] = None
    
    return video_url_mapping

def test_video_search():
    """Test the video search functionality"""
    test_text = "London city tour with Big Ben and Buckingham Palace"
    
    print("🔍 Testing video search...")
    print(f"📝 Search text: {test_text}")
    
    try:
        result = search_video_url(test_text)
        if result and hasattr(result[0], 'path'):
            print(f"✅ Found video URL: {result[0].path}")
        else:
            print("❌ No video URL found")
    except Exception as e:
        print(f"❌ Error in test: {str(e)}")

def test_video_url_mapping():
    """Test the video URL mapping functionality"""
    # Example script mapping
    test_mapping = {
        1: "[Show dynamic montage of London landmarks]",
        5: "[Show Buckingham Palace footage]",
        10: "[Show Houses of Parliament and Big Ben]"
    }
    
    print("\n🧪 Testing video URL mapping...")
    video_url_mapping = create_video_url_mapping(test_mapping)
    
    print("\n📊 Results:")
    for position, url in video_url_mapping.items():
        print(f"Position {position}: {url}")

if __name__ == "__main__":
    test_video_search()
    test_video_url_mapping() 