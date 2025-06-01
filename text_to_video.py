import os
import asyncio
import fal_client
from typing import Optional, Callable, Dict, Any, AsyncGenerator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TextToVideo:
    def __init__(self):
        """Initialize the TextToVideo client."""
        self.api_key = os.getenv('FAL_KEY')
        if not self.api_key:
            raise ValueError("FAL_KEY not found in environment variables")
        
        # Configure fal client with credentials
        fal_client.credentials = self.api_key
        
        # Available avatars
        self.avatars = [
            "emily_primary", "emily_side",
            "marcus_primary", "marcus_side",
            "aisha_walking", "elena_primary",
            "elena_side", "any_male_primary",
            "any_female_primary", "any_male_side",
            "any_female_side"
        ]

    def _on_queue_update(self, update: Any) -> None:
        """Handle queue updates and print status messages."""
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"Status: {log['message']}")

    def generate_video_sync(
        self,
        text: str,
        avatar_id: str = "emily_primary",
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate video synchronously (will wait for completion).
        
        Args:
            text: The text to convert to video
            avatar_id: The avatar to use (default: emily_primary)
            on_status_update: Optional callback for status updates
            
        Returns:
            Dict containing the video information
        """
        if avatar_id not in self.avatars:
            raise ValueError(f"Invalid avatar_id. Must be one of: {self.avatars}")

        # Define status update handler
        def status_handler(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    status_msg = log['message']
                    print(f"Status: {status_msg}")
                    if on_status_update:
                        on_status_update(status_msg)

        try:
            # Submit request and wait for completion
            result = fal_client.subscribe(
                "veed/avatars/text-to-video",
                arguments={
                    "avatar_id": avatar_id,
                    "text": text
                },
                with_logs=True,
                on_queue_update=status_handler
            )
            
            return result
            
        except Exception as e:
            print(f"Error generating video: {str(e)}")
            raise

    async def generate_video_async(
        self,
        text: str,
        avatar_id: str = "emily_primary",
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate video asynchronously.
        
        Args:
            text: The text to convert to video
            avatar_id: The avatar to use (default: emily_primary)
            on_status_update: Optional callback for status updates
            
        Returns:
            Dict containing the video information
        """
        if avatar_id not in self.avatars:
            raise ValueError(f"Invalid avatar_id. Must be one of: {self.avatars}")

        try:
            print("📤 Submitting video generation request...")
            # Submit request
            handler = fal_client.submit(
                "veed/avatars/text-to-video",
                arguments={
                    "avatar_id": avatar_id,
                    "text": text
                }
            )
            
            request_id = handler.request_id
            print(f"📥 Request submitted. ID: {request_id}")
            
            # Poll for status until complete
            while True:
                print("🔄 Checking status...")
                status = fal_client.status(
                    "veed/avatars/text-to-video",
                    request_id,
                    with_logs=True
                )
                
                print(f"📊 Status response type: {type(status)}")
                
                # Handle status updates
                if isinstance(status, dict):
                    status_type = status.get('status', '')
                    print(f"📋 Status type: {status_type}")
                    
                    if status_type == 'IN_PROGRESS':
                        for log in status.get('logs', []):
                            status_msg = log.get('message', '')
                            print(f"📝 Status: {status_msg}")
                            if on_status_update:
                                on_status_update(status_msg)
                    elif status_type == 'COMPLETED':
                        print("✅ Video generation completed!")
                        # Get the result using result_async
                        result = await fal_client.result_async(
                            "veed/avatars/text-to-video",
                            request_id
                        )
                        return result
                    elif status_type == 'FAILED':
                        error_msg = status.get('error', 'Unknown error')
                        raise Exception(f"Video generation failed: {error_msg}")
                elif isinstance(status, fal_client.client.Completed):
                    print("✅ Video generation completed!")
                    # Get the result using result_async
                    result = await fal_client.result_async(
                        "veed/avatars/text-to-video",
                        request_id
                    )
                    return result
                else:
                    print(f"⚠️ Unexpected status format: {type(status)}")
                
                # Wait a bit before next status check
                print("⏳ Waiting 2 seconds before next status check...")
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"❌ Error in generate_video_async: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
            raise

    async def generate_video_stream(
        self,
        text: str,
        avatar_id: str = "emily_primary",
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate video with streaming updates.
        
        Args:
            text: The text to convert to video
            avatar_id: The avatar to use (default: emily_primary)
            on_status_update: Optional callback for status updates
            
        Yields:
            Dict containing status updates and eventually the video information
        """
        if avatar_id not in self.avatars:
            raise ValueError(f"Invalid avatar_id. Must be one of: {self.avatars}")

        try:
            print("📤 Submitting video generation request...")
            # Submit request
            handler = fal_client.submit(
                "veed/avatars/text-to-video",
                arguments={
                    "avatar_id": avatar_id,
                    "text": text
                }
            )
            
            request_id = handler.request_id
            print(f"📥 Request submitted. ID: {request_id}")
            
            # Stream status updates
            async for update in fal_client.stream_status(
                "veed/avatars/text-to-video",
                request_id
            ):
                if isinstance(update, dict):
                    status_type = update.get('status', '')
                    
                    if status_type == 'IN_PROGRESS':
                        for log in update.get('logs', []):
                            status_msg = log.get('message', '')
                            print(f"📝 Status: {status_msg}")
                            if on_status_update:
                                on_status_update(status_msg)
                            yield {"type": "status", "message": status_msg}
                    elif status_type == 'COMPLETED':
                        print("✅ Video generation completed!")
                        result = await fal_client.result_async(
                            "veed/avatars/text-to-video",
                            request_id
                        )
                        yield {"type": "complete", "result": result}
                        return
                    elif status_type == 'FAILED':
                        error_msg = update.get('error', 'Unknown error')
                        raise Exception(f"Video generation failed: {error_msg}")
                
        except Exception as e:
            print(f"❌ Error in generate_video_stream: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
            raise

# Example usage
if __name__ == "__main__":
    # Initialize the client
    ttv = TextToVideo()
    
    # Example text
    sample_text = """
    Welcome to our product demonstration!
    This is a sample video generated using AI.
    We can create engaging content quickly and efficiently.
    """
    
    # Example status update callback
    def status_callback(status: str):
        print(f"Custom status update: {status}")
    
    try:
        # Synchronous example
        print("\nGenerating video synchronously...")
        result = ttv.generate_video_sync(
            text=sample_text,
            avatar_id="emily_primary",
            on_status_update=status_callback
        )
        print(f"Video generated successfully! URL: {result['video']['url']}")
        
        # Asynchronous example (uncomment to use)
        """
        print("\nGenerating video asynchronously...")
        import asyncio
        result = asyncio.run(ttv.generate_video_async(
            text=sample_text,
            avatar_id="emily_primary",
            on_status_update=status_callback
        ))
        print(f"Video generated successfully! URL: {result['video']['url']}")
        """
        
    except Exception as e:
        print(f"Error: {str(e)}") 