from video_inserter import VideoInserter
import os

def main():
    # Initialize the video inserter
    inserter = VideoInserter()
    
    # Your input paths
    main_video = "file:///var/folders/16/s_n1kphx5d94s154lx9wnmf00000gn/T/tmp1js4plbo.mp4"
    insert_video = "file:///var/folders/16/s_n1kphx5d94s154lx9wnmf00000gn/T/tmp2su3rz31.mp4"
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Output path
    output_path = os.path.join(output_dir, "output_video_multiple.mp4")
    
    try:
        # Create a list of tuples with video paths and timestamps
        video_timestamps = [
            (insert_video, 5.0),   # First insertion at 5 seconds
            (insert_video, 10.0),  # Second insertion at 10 seconds
            (insert_video, 15.0)   # Third insertion at 15 seconds
        ]
        
        # Insert multiple videos
        result_path = inserter.insert_multiple_videos(
            main_video_path=main_video,
            video_timestamps=video_timestamps,
            output_path=output_path
        )
        print(f"Success! Output video saved to: {result_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 