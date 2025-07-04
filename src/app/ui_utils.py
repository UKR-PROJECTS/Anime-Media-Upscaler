"""
This module provides utility functions for the user interface.

It includes functions for:
- Formatting time durations into a human-readable string.
- Recursively collecting all supported media files from a given directory.
- Verifying that all required external dependencies (FFmpeg, Real-ESRGAN) are available.
"""
import os
import shutil
from pathlib import Path
from typing import List
from PyQt6.QtWidgets import QMessageBox

def format_time(seconds: float) -> str:
    """
    Formats a time duration in seconds into a human-readable string (HH:MM:SS or MM:SS).

    Args:
        seconds: The time duration in seconds.

    Returns:
        A formatted time string.
    """
    # Calculate hours, minutes, and seconds
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    # Return the formatted string
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def get_files_from_directory(directory: str) -> List[str]:
    """
    Recursively collects all supported media files from a given directory.

    Args:
        directory: The path to the directory to search.

    Returns:
        A list of paths to the supported media files.
    """
    # Define supported file extensions
    supported_extensions = {
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp',
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'
    }
    files = []
    # Walk through the directory and collect files with supported extensions
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if Path(filename).suffix.lower() in supported_extensions:
                files.append(os.path.join(root, filename))
    return files

def check_dependencies() -> bool:
    """
    Verifies that all required external dependencies (FFmpeg, Real-ESRGAN) are available.

    Returns:
        True if all dependencies are found, False otherwise.
    """
    errors = []

    # Check for FFmpeg
    try:
        ffmpeg_path = 'bin/ffmpeg.exe' if os.name == 'nt' else 'bin/ffmpeg'
        if not os.path.isfile(ffmpeg_path):
            if not shutil.which('ffmpeg'):
                errors.append("FFmpeg not found. Please ensure ffmpeg is in the bin folder or in PATH.")
    except Exception:
        errors.append("FFmpeg check failed")

    # Check for Real-ESRGAN
    realesrgan_found = False
    possible_names = [
        'realesrgan-ncnn-vulkan', 'realesrgan-ncnn-vulkan.exe',
        'realsr-esrgan', 'realsr-esrgan.exe'
    ]
    for path in ['.', 'bin']:
        for name in possible_names:
            if os.path.isfile(os.path.join(path, name)):
                realesrgan_found = True
                break
        if realesrgan_found:
            break
    if not realesrgan_found:
        for name in possible_names:
            if shutil.which(name):
                realesrgan_found = True
                break
    if not realesrgan_found:
        errors.append("Real-ESRGAN executable not found. Please install Real-ESRGAN.")

    # If there are errors, show a message box
    if errors:
        error_msg = "Missing dependencies:\n\n" + "\n".join(f"• {error}" for error in errors)
        error_msg += "\n\nPlease check the installation instructions."
        QMessageBox.critical(None, "Dependency Error", error_msg)
        return False
    return True
