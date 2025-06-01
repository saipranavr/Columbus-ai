from moviepy.editor import VideoFileClip, CompositeVideoClip
from typing import Dict, Union, List
import os
from urllib.parse import unquote

class VideoInserter:
    def __init__(self):
        """Initialize the VideoInserter class."""
        pass

    def _clean_path(self, path: str) -> str:
        """Convert URL format path to regular file path."""
        if path.startswith('file://'):
            return unquote(path[7:])  # Remove 'file://' and decode URL
        return path

    def insert_video(
        self,
        main_video_path: str,
        insert_video_path: str,
        timestamp: float,
        output_path: str,
        insert_duration: float = 3.0  # Default duration for inserted video
    ) -> str:
        """
        Insert a second video into the main video at a specific timestamp while preserving the main video's audio.
        
        Args:
            main_video_path (str): Path to the main video file
            insert_video_path (str): Path to the video to be inserted
            timestamp (float): Time in seconds where the second video should be inserted
            output_path (str): Path where the output video should be saved
            insert_duration (float): Duration in seconds for the inserted video (default: 3.0)
            
        Returns:
            str: Path to the output video file
        """
        # Clean the paths
        main_video_path = self._clean_path(main_video_path)
        insert_video_path = self._clean_path(insert_video_path)
        
        # Load the videos
        main_video = VideoFileClip(main_video_path)
        insert_video = VideoFileClip(insert_video_path)
        
        # Limit the duration of the inserted video
        insert_video = insert_video.subclip(0, min(insert_duration, insert_video.duration))
        
        # Get the audio from the main video
        main_audio = main_video.audio
        
        # Create a new video clip that's the same duration as the main video
        final_video = main_video.set_duration(main_video.duration)
        
        # Set the position and duration for the inserted video
        insert_video = insert_video.set_start(timestamp)
        
        # Composite the videos
        final_video = CompositeVideoClip([final_video, insert_video])
        
        # Set the audio from the main video
        final_video = final_video.set_audio(main_audio)
        
        # Write the result to a file
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Close the video clips to free up resources
        main_video.close()
        insert_video.close()
        final_video.close()
        
        return output_path

    def insert_multiple_videos(
        self,
        main_video_path: str,
        video_timestamps: Dict[str, float],
        output_path: str,
        insert_duration: float = 3.0  # Default duration for inserted videos
    ) -> str:
        """
        Insert multiple videos into the main video at specified timestamps while preserving the main video's audio.
        
        Args:
            main_video_path (str): Path to the main video file
            video_timestamps (Dict[str, float]): Dictionary mapping video paths to their insertion timestamps
            output_path (str): Path where the output video should be saved
            insert_duration (float): Duration in seconds for each inserted video (default: 3.0)
            
        Returns:
            str: Path to the output video file
        """
        # Clean the main video path
        main_video_path = self._clean_path(main_video_path)
        
        # Load the main video
        main_video = VideoFileClip(main_video_path)
        main_audio = main_video.audio
        
        # Create a list to hold all video clips
        video_clips = [main_video]
        
        # Add each video at its specified timestamp
        for video_path, timestamp in video_timestamps.items():
            # Clean the video path
            clean_path = self._clean_path(video_path)
            insert_video = VideoFileClip(clean_path)
            
            # Limit the duration of the inserted video
            insert_video = insert_video.subclip(0, min(insert_duration, insert_video.duration))
            
            insert_video = insert_video.set_start(timestamp)
            video_clips.append(insert_video)
        
        # Composite all videos
        final_video = CompositeVideoClip(video_clips)
        
        # Set the audio from the main video
        final_video = final_video.set_audio(main_audio)
        
        # Write the result to a file
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Close all video clips
        for clip in video_clips:
            clip.close()
        final_video.close()
        
        return output_path 