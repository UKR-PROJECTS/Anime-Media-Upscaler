# Usage Guide

A comprehensive guide on how to use Sharpify GUI - a PyQt6-based desktop app to upscale images and videos using Real-ESRGAN.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [User Interface Guide](#user-interface-guide)
- [Supported File Types](#supported-file-types)
- [Upscaling Options](#upscaling-options)
- [Advanced Settings](#advanced-settings)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)
- [FAQ](#faq)

## Overview

Sharpify GUI is a professional-grade tool designed to upscale images and videos efficiently. Built with PyQt6, it provides an intuitive desktop interface for:

- **Image Upscaling**: Upscale JPG, PNG, BMP, TIFF, and WebP images by 4x.
- **Video Upscaling**: Upscale MP4, AVI, MKV, MOV, WMV, and FLV videos by 4x.
- **Batch Processing**: Enqueue multiple files for sequential processing with progress tracking.
- **Model Selection**: Choose between different Real-ESRGAN models optimized for various content types.
- **GPU Acceleration**: Leverage CUDA/OpenCL for significantly faster upscaling.
- **Advanced Configuration**: Fine-tune settings like tile size, output format, FPS, and quality.
- **Comprehensive Logging**: Keep track of the upscaling process with detailed, timestamped logs.

## Quick Start

### Prerequisites

- Windows Operating System
- A modern GPU with support for Vulkan.
- Git (for cloning the repository)

### Installation

#### Clone from GitHub

```bash
# Clone the repository
git clone https://github.com/uikraft-hub/sharpify-gui.git

# Navigate to the project directory
cd sharpify-gui

# Install required dependencies
pip install -r requirements.txt
```

## Running the Application

1.  **Navigate to the `src` directory:**
    ```bash
    cd src
    ```
2.  **Run the application:**
    ```bash
    python main.py
    ```

The application window will open, and you can start using it.

## User Interface Guide

### Main Interface Components

#### 1. Left Panel
- **Input Files**: Add files and folders to the processing queue. You can also drag and drop files here.
- **Output Settings**: Select the folder where the upscaled files will be saved.
- **Quick Settings**: Quickly select the upscaling model.
- **Controls**: Start/stop the upscaling process and access advanced settings.

#### 2. Right Panel
- **Progress**: View the progress of the current file and the overall batch.
- **Processing Log**: See detailed, timestamped logs of the upscaling process.

## Supported File Types

### Image Formats
- JPG
- JPEG
- PNG
- BMP
- TIFF
- WebP

### Video Formats
- MP4
- AVI
- MKV
- MOV
- WMV
- FLV

## Upscaling Options

### Model Selection
You can choose from the following Real-ESRGAN models:
-   **Anime Image/Video 4x**: Optimized for upscaling anime-style images and videos.
-   **General Image/Video 4x**: A general-purpose model for all other types of images and videos.
-   **Anime Photos 4x**: A model specifically for anime-style photos.

### Output Format
For images, you can choose the output format:
-   **JPG**: Good for photos, smaller file size.
-   **PNG**: Lossless format, good for graphics.
-   **WebP**: Modern format with good compression.

Videos are output in the same format as the input file.

## Advanced Settings

You can access the advanced settings by clicking the "Advanced Settings" button.

### AI Model Settings
-   **Model**: Select the Real-ESRGAN model to use.

### Performance Settings
-   **Use GPU Acceleration**: Enable or disable GPU usage.
-   **Tile Size**: Controls GPU memory usage. Lower values use less memory but are slower.

### Video Processing Settings
-   **Output FPS**: Set the frames per second for the output video.
-   **Video Quality (CRF)**: Control the quality of the output video. Lower values mean higher quality and larger file sizes.

### Output Format Settings
-   **Image Format**: Choose the output format for upscaled images.

## Troubleshooting

### Common Issues and Solutions

#### Application does not start
**Possible Causes:**
- Missing dependencies.
- Python is not installed correctly.

**Solutions:**
1.  Make sure you have installed all the dependencies from `requirements.txt`.
2.  Ensure you are using a supported version of Python.

#### Upscaling fails
**Possible Causes:**
- The input file is corrupted.
- The selected model is not compatible with the input file.
- Insufficient GPU memory.

**Solutions:**
1.  Try a different input file.
2.  Try a different upscaling model.
3.  If using GPU, try reducing the tile size in the advanced settings.

## Best Practices

### Performance Optimization
- Use GPU acceleration for the best performance.
- Adjust the tile size based on your GPU's memory.
- Process files in batches to save time.

### File Management
- Organize your input and output files in separate folders.
- Use the "Clear All" button to clear the file queue before starting a new batch.

## API Reference

The application is not designed to be used as a library, but the core logic is contained in the following classes:

### Core Classes

#### `app.main_window.AnimeUpscalerGUI`
The main application window.

#### `app.workers.UpscaleWorker`
Handles the upscaling process in a separate thread.

## FAQ

### General Questions

**Q: Is this application free to use?**
A: Yes, this is an open-source project under the MIT license.

**Q: Do I need a powerful computer to run this application?**
A: A modern GPU is recommended for the best performance, but the application can also run on the CPU.

### Technical Questions

**Q: Can I use my own Real-ESRGAN models?**
A: Currently, you can only use the models included with the application.

**Q: Where are the upscaled files saved?**
A: You can select the output folder using the "Select Output Folder" button.

## 📞 Support

- **📧 Email**: [ujjwalkrai@gmail.com](mailto:ujjwalkrai@gmail.com)
- **🐛 Issues**: [Repository Issues](https://github.com/uikraft-hub/sharpify-gui/issues)
- **🔓 Security**: [Repository Security](https://github.com/uikraft-hub/sharpify-gui/security)
- **⛏ Pull Requests**: [Repository Pull Requests](https://github.com/uikraft-hub/sharpify-gui/pulls)
- **📖 Documentation**: [Repository Documentation](https://github.com/uikraft-hub/sharpify-gui/tree/main/docs)
