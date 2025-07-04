"""
Anime Media Upscaler - Professional Anime Image and Video Upscaling Application
===============================================================================

A comprehensive PyQt6-based GUI application for upscaling anime images and videos
using Real-ESRGAN AI models with advanced batch processing capabilities.

Author: Ujjwal Nova
Version: 2.0.0
License: MIT
Repository: https://github.com/UKR-PROJECTS/Anime-Media-Upscaler

Key Features:
- Batch processing of images and videos with 2x, 3x, and 4x upscaling
- Multi-threaded processing with progress tracking
- Professional drag-and-drop interface
- Multiple AI models (Real-ESRGAN variants)
- GPU acceleration support
- Advanced settings configuration
- Comprehensive logging system

Technical Requirements:
- PyQt6: Modern GUI framework
- Real-ESRGAN: AI upscaling engine (realesrgan-ncnn-vulkan.exe)
- FFmpeg: Video processing toolkit (external binary)
- Python 3.8+

Supported Formats:
- Images: JPG, PNG, BMP, TIFF, WebP
- Videos: MP4, AVI, MKV, MOV, WMV, FLV

Installation & Usage:
1. Ensure Real-ESRGAN and FFmpeg binaries are in 'bin/' folder or PATH
2. Run: python main.py
3. Add files via drag-and-drop or file browser
4. Configure settings and start processing
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app.main_window import AnimeUpscalerGUI

def main():
    """
    Main application entry point.
    Initializes the QApplication and main window.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Anime-Media-Upscaler")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("UKR-PROJECTS")

    icon_path = 'favicon.ico'
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = AnimeUpscalerGUI()
    window.show()

    window.log("Anime-Media-Upscaler v2.0.0 started")
    window.log("Checking dependencies...")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

