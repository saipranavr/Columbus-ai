import asyncio
from text_to_video import TextToVideo

async def test_async_video():
    # Initialize the client
    ttv = TextToVideo()
    
    # Test text
    test_text = """
    This is a test video.
    We are testing the async functionality.
    This should take a few moments to complete.
    """
    
    # Status update callback
    def status_callback(status: str):
        print(f"🔄 Status Update: {status}")
    
    print("🚀 Starting async video generation...")
    print("📝 Using text:", test_text.strip())
    print("👤 Using avatar: emily_primary")
    
    try:
        print("📡 Submitting request to API...")
        # Start the async video generation
        result = await ttv.generate_video_async(
            text=test_text,
            avatar_id="emily_primary",
            on_status_update=status_callback
        )
        
        # If we get here, the video is ready
        print("\n✅ Video generation completed!")
        print(f"📺 Video URL: {result['video']['url']}")
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        print("🔍 Error details:", type(e).__name__)
        raise

if __name__ == "__main__":
    print("🧪 Running async video generation test...")
    try:
        asyncio.run(test_async_video())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}") 