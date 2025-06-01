# Video Inserter

A Python module for inserting videos into a main video while preserving the original audio. This tool is particularly useful for creating picture-in-picture effects or inserting multiple video clips at specific timestamps.

## Features

- Insert a single video at a specific timestamp
- Insert multiple videos (or the same video multiple times) at different timestamps
- Preserve the original audio from the main video
- Configurable duration for inserted videos (default: 3 seconds)
- Handles URL-formatted file paths
- Proper resource management and cleanup

## Requirements

- Python 3.x
- moviepy
- ffmpeg (system dependency)

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install ffmpeg (if not already installed):
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Usage

### Basic Usage - Single Video Insertion

```python
from video_inserter import VideoInserter

# Initialize the inserter
inserter = VideoInserter()

# Insert a single video
result_path = inserter.insert_video(
    main_video_path="path/to/main/video.mp4",
    insert_video_path="path/to/insert/video.mp4",
    timestamp=5.0,  # Insert at 5 seconds
    output_path="path/to/output/video.mp4",
    insert_duration=3.0  # Optional: duration of inserted video (default: 3.0 seconds)
)
```

### Multiple Video Insertions

```python
from video_inserter import VideoInserter

# Initialize the inserter
inserter = VideoInserter()

# Create a list of video insertions
video_timestamps = [
    ("path/to/video1.mp4", 5.0),   # Insert video1 at 5 seconds
    ("path/to/video2.mp4", 10.0),  # Insert video2 at 10 seconds
    ("path/to/video1.mp4", 15.0)   # Insert video1 again at 15 seconds
]

# Insert multiple videos
result_path = inserter.insert_multiple_videos(
    main_video_path="path/to/main/video.mp4",
    video_timestamps=video_timestamps,
    output_path="path/to/output/video.mp4",
    insert_duration=3.0  # Optional: duration of inserted videos (default: 3.0 seconds)
)
```

### URL-formatted Paths

The module can handle URL-formatted file paths (e.g., `file:///path/to/video.mp4`). The paths will be automatically converted to regular file paths.

## API Reference

### VideoInserter Class

#### `__init__()`
Initialize the VideoInserter class.

#### `insert_video(main_video_path: str, insert_video_path: str, timestamp: float, output_path: str, insert_duration: float = 3.0) -> str`
Insert a single video at a specific timestamp.

Parameters:
- `main_video_path`: Path to the main video file
- `insert_video_path`: Path to the video to be inserted
- `timestamp`: Time in seconds where the video should be inserted
- `output_path`: Path where the output video should be saved
- `insert_duration`: Duration in seconds for the inserted video (default: 3.0)

Returns:
- Path to the output video file

#### `insert_multiple_videos(main_video_path: str, video_timestamps: List[Tuple[str, float]], output_path: str, insert_duration: float = 3.0) -> str`
Insert multiple videos at specified timestamps.

Parameters:
- `main_video_path`: Path to the main video file
- `video_timestamps`: List of tuples containing (video_path, timestamp)
- `output_path`: Path where the output video should be saved
- `insert_duration`: Duration in seconds for each inserted video (default: 3.0)

Returns:
- Path to the output video file

## Notes

1. The main video's audio is preserved throughout the entire duration of the output video.
2. All inserted videos are limited to the specified duration (default: 3 seconds).
3. The output video will have the same duration as the main video.
4. The module automatically handles resource cleanup (closing video files).
5. URL-formatted paths are automatically converted to regular file paths.

## Example

See `test_video_inserter.py` for a complete example of how to use the module.

## Error Handling

The module includes basic error handling for:
- File not found errors
- Invalid video formats
- Resource cleanup

## Future Improvements

Potential areas for enhancement:
1. Support for different video positions (currently only supports overlay)
2. Custom audio mixing options
3. Video scaling and positioning options
4. Progress callback for long operations
5. Support for different output formats and codecs 