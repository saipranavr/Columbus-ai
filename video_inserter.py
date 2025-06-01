from moviepy.editor import VideoFileClip, CompositeVideoClip, ColorClip, vfx
from typing import Dict, Union, List, Tuple
import os
from urllib.parse import unquote

class VideoInserter:
    def __init__(self):
        """Initialize the VideoInserter class."""
        self.main_video = None
        self.inserted_videos = []

    def _clean_path(self, path: str) -> str:
        """Convert URL format path to regular file path."""
        if path.startswith('file://'):
            return unquote(path[7:])  # Remove 'file://' and decode URL
        return path

    def _prepare_inserted_video(self, video_path: str, main_width: int, main_height: int) -> VideoFileClip:
        """Prepare an inserted video by scaling and centering it within the main video dimensions."""
        try:
            # Load the video
            video = VideoFileClip(video_path)
            
            # Limit duration to 5 seconds
            video = video.subclip(0, min(5, video.duration))
            
            # Calculate scaling factors for both dimensions
            width_scale = main_width / video.w
            height_scale = main_height / video.h
            
            # Use the smaller scale to ensure the video fits within the frame
            scale_factor = min(width_scale, height_scale)
            
            # Scale the video using a simple resize
            scaled_video = video.resize(scale_factor)
            
            # Calculate position to center the video
            x_pos = (main_width - scaled_video.w) / 2
            y_pos = (main_height - scaled_video.h) / 2
            
            # Set the position
            positioned_video = scaled_video.set_position((x_pos, y_pos))
            
            return positioned_video
        except Exception as e:
            print(f"Error preparing video {video_path}: {str(e)}")
            raise

    def insert_video(self, main_video_path: str, inserted_video_path: str, 
                    timestamp: float, output_path: str) -> str:
        """
        Insert a second video at a specified timestamp in the first video.
        
        Args:
            main_video_path: Path to the main video
            inserted_video_path: Path to the video to be inserted
            timestamp: Time in seconds where the video should be inserted
            output_path: Path where the output video should be saved
            
        Returns:
            Path to the output video
        """
        try:
            # Load the main video
            self.main_video = VideoFileClip(main_video_path)
            
            # Load and prepare the inserted video
            inserted_video = self._prepare_inserted_video(
                inserted_video_path,
                self.main_video.w,
                self.main_video.h
            )
            
            # Set the start time for the inserted video
            inserted_video = inserted_video.set_start(timestamp)
            
            # Composite the videos
            final_video = CompositeVideoClip([self.main_video, inserted_video])
            
            # Write the result
            final_video.write_videofile(output_path)
            
            return output_path
            
        finally:
            # Clean up
            if self.main_video:
                self.main_video.close()
            for video in self.inserted_videos:
                video.close()
            self.main_video = None
            self.inserted_videos = []

    def insert_multiple_videos(self, main_video_path: str, 
                             video_timestamps: list[tuple[str, float]], 
                             output_path: str) -> str:
        """
        Insert multiple videos at different timestamps in the main video.
        
        Args:
            main_video_path: Path to the main video
            video_timestamps: List of tuples containing (video_path, timestamp)
            output_path: Path where the output video should be saved
            
        Returns:
            Path to the output video
        """
        try:
            # Load the main video
            self.main_video = VideoFileClip(main_video_path)
            main_duration = self.main_video.duration
            
            # Create a semi-transparent black overlay for the background
            overlay = ColorClip(size=(self.main_video.w, self.main_video.h), 
                              color=(0, 0, 0))
            overlay = overlay.set_opacity(0.3)  # 30% opacity
            
            # Prepare all inserted videos
            clips = [self.main_video]  # Start with the main video
            for video_path, timestamp in video_timestamps:
                # Skip if timestamp is beyond main video duration
                if timestamp >= main_duration:
                    print(f"⚠️ Skipping video at {timestamp}s (beyond main video duration of {main_duration}s)")
                    continue
                    
                inserted_video = self._prepare_inserted_video(
                    video_path,
                    self.main_video.w,
                    self.main_video.h
                )
                
                # Add fade in/out effects
                inserted_video = inserted_video.crossfadein(0.5).crossfadeout(0.5)
                
                # Set the start time
                inserted_video = inserted_video.set_start(timestamp)
                
                # Add the overlay for this segment
                overlay_segment = overlay.set_duration(inserted_video.duration)
                overlay_segment = overlay_segment.set_start(timestamp)
                
                clips.extend([overlay_segment, inserted_video])
                self.inserted_videos.extend([inserted_video, overlay_segment])
            
            # Composite all videos
            final_video = CompositeVideoClip(clips)
            
            # Set the audio from the main video
            final_video = final_video.set_audio(self.main_video.audio)
            
            # Write the result
            final_video.write_videofile(output_path)
            
            return output_path
            
        finally:
            # Clean up
            if self.main_video:
                self.main_video.close()
            for video in self.inserted_videos:
                video.close()
            self.main_video = None
            self.inserted_videos = []

if __name__ == "__main__":
    # Test with hardcoded script and video paths
    script = """Hey globetrotters! Welcome back to the channel! Today, we're diving headfirst into one of the world's most iconic cities: London! [Show vibrant montage of London landmarks] Get ready for a whirlwind tour packed with famous sights, delicious food, and some seriously cool hidden gems. First up, the must-see landmarks. [Show footage of Buckingham Palace] Buckingham Palace, of course! Did you know that the State Rooms, where the Queen would receive guests, are only open to the public during the summer months? Definitely worth a visit if you're planning a summer trip. [Show footage of Houses of Parliament and Big Ben]"""
    
    # Create test video timestamps (roughly 1 word per second)
    video_timestamps = [
        ("video1.mp4", 20.0),  # London landmarks
        ("video2.mp4", 45.0),  # Buckingham Palace
        ("video3.mp4", 72.0),  # Houses of Parliament
    ]
    
    inserter = VideoInserter()
    result = inserter.insert_multiple_videos(
        main_video_path="talking_head.mp4",
        video_timestamps=video_timestamps,
        output_path="output/final_video.mp4"
    )
    print(f"✅ Video created at: {result}") 