from video_inserter import VideoInserter
import os

def main():
    # Initialize the video inserter
    inserter = VideoInserter()
    
    # Your input paths
    main_video = "file:///var/folders/16/s_n1kphx5d94s154lx9wnmf00000gn/T/tmp1js4plbo.mp4"
    insert_video = "file:///var/folders/16/s_n1kphx5d94s154lx9wnmf00000gn/T/tmp2su3rz31.mp4"
    timestamp = 2.0  # 2 seconds
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Output path
    output_path = os.path.join(output_dir, "output_video.mp4")
    
    try:
        # Insert the video
        result_path = inserter.insert_video(
            main_video_path=main_video,
            insert_video_path=insert_video,
            timestamp=timestamp,
            output_path=output_path
        )
        print(f"Success! Output video saved to: {result_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 