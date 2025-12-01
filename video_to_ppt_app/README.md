# Video to PowerPoint Converter

A web application that converts presentation videos (MP4) into PowerPoint slides by extracting distinct frames.

## Features

- Upload MP4 video files through a modern web interface
- Automatically detects distinct slides using frame difference analysis
- **Removes NotebookLM logo** from bottom right corner of each slide
- Generates PowerPoint presentations with extracted slides
- Download the resulting PPTX file

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Upload an MP4 video file using the web interface

4. Wait for processing to complete (this may take a minute or two depending on video length)

5. Download the generated PowerPoint presentation

## How It Works

The app uses computer vision techniques to identify distinct slides:

1. **Frame Extraction**: Reads the video frame by frame
2. **Change Detection**: Compares consecutive frames using pixel difference analysis
3. **Slide Identification**: When significant changes are detected (threshold exceeded) and enough time has passed, a new slide is identified
4. **PowerPoint Generation**: Extracted slides are formatted and added to a PowerPoint presentation

## Configuration

You can adjust the slide detection sensitivity and logo removal by modifying parameters in `app.py`:

**Slide Detection:**
- `threshold`: Pixel difference threshold (default: 25). Lower values = more sensitive
- `min_time_between_slides`: Minimum seconds between detected slides (default: 2.0)

**Logo Removal:**
- `logo_height_percent`: Percentage of frame height to crop from bottom (default: 8%)
- Set `remove_logo_flag=False` in `extract_unique_frames()` to disable logo removal

## Technical Details

- **Backend**: Flask web framework
- **Video Processing**: OpenCV (cv2)
- **PowerPoint Generation**: python-pptx
- **Image Processing**: NumPy

## Testing

Run the test script to verify functionality:
```bash
python test_processing.py
```

This will process a sample video and generate a test PowerPoint file in the `outputs/` directory.
