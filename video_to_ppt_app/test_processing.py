"""Test script to verify video processing works correctly."""
import os
import sys
from app import extract_unique_frames, create_powerpoint

# Test with a sample video
video_path = r"C:\Users\kerry\repos\mgmt638\videos\Factor_Investing.mp4"
output_path = "outputs/test_presentation_no_logo.pptx"

print(f"Testing video processing with logo removal")
print(f"Video: {video_path}")
print("-" * 60)

try:
    # Create output directory if needed
    os.makedirs("outputs", exist_ok=True)

    # Extract frames with logo removal
    print("Extracting unique frames (with logo removal)...")
    frames = extract_unique_frames(video_path, threshold=25, min_time_between_slides=2.0, remove_logo_flag=True)
    print(f"[OK] Extracted {len(frames)} unique slides")

    # Show frame dimensions
    if frames:
        height, width = frames[0].shape[:2]
        print(f"[OK] Frame dimensions after cropping: {width}x{height}")

    # Create PowerPoint
    print("Creating PowerPoint presentation...")
    create_powerpoint(frames, output_path)
    print("[OK] PowerPoint created successfully")

    # Verify output
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[OK] Output file exists: {output_path}")
        print(f"  File size: {size_mb:.2f} MB")
        print("\n" + "=" * 60)
        print("SUCCESS! The app is working correctly.")
        print("=" * 60)
    else:
        print("[ERROR] Output file was not created")
        sys.exit(1)

except Exception as e:
    print(f"\n[ERROR] Error during processing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
