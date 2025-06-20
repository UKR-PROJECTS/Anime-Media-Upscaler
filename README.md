# Media-Upscaler v1.0.0
[![Status](https://img.shields.io/badge/status-active-47c219.svg)](#) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
<p align="center">
  <img src="resources/logo.png" width="300" height="300" alt="SSTube Icon" />
</p>

SSUpscaler is a Python-based desktop application designed to upscale videos and images using advanced interpolation techniques. Built with PyQt6 for the graphical interface and OpenCV for media processing, this tool allows users to convert their media files to higher resolutions (1080p, 2K, or 4K) quickly and efficiently. It also preserves audio tracks for videos using FFmpeg.

---

## Description

SSUpscaler offers an easy-to-use, graphical interface for batch processing media files. With support for various video and image formats, users can upscale their content using different interpolation methods such as Nearest, Linear, Cubic, and Lanczos. The application provides real-time progress feedback and error handling to ensure a smooth upscaling experience.

Key features include:
- **Batch Processing:** Add multiple media files and process them in one go.
- **Resolution Options:** Choose between 1080p, 2K, or 4K output.
- **Interpolation Methods:** Select the desired interpolation algorithm for optimal quality.
- **Audio Preservation:** Automatically extracts and re-attaches audio for video files (using FFmpeg).
- **Professional UI:** A dark-themed, intuitive user interface built with PyQt6.

---

## Installation Instructions

### Prerequisites

- **Python 3.8+** – Ensure Python is installed on your system.
- **FFmpeg for Windows:** The project expects `ffmpeg.exe` to be located in the `bin/` directory.  
  *Note: For non-Windows users, please download the appropriate FFmpeg binary and adjust the path in the source code accordingly.*

### Steps

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/UKR-PROJECTS/SSUpscaler.git
   cd SSUpscaler
   ```

2. **Create a Virtual Environment (Optional but Recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   Ensure you have [pip](https://pip.pypa.io/) installed, then run:

   ```bash
   pip install -r requirements.txt
   ```

   *Example `requirements.txt` might include:*
   ```
   PyQt6
   opencv-python
   ```

4. **Verify Project Structure:**

   The recommended structure should look like this:

   ```
   SSUpscaler/
   ├── bin/
   │   └── ffmpeg.exe
   ├── resources/
   │   ├── folder.png
   │   ├── loader.gif
   │   └── logo.png
   ├── src/
   │   └── main.py
   ├── tests/
   │   └── test_basic.py
   ├── .gitignore
   ├── README.md
   └── requirements.txt
   ```

---

## Usage

1. **Start the Application:**

   Navigate to the `src/` directory and run the main script:

   ```bash
   python main.py
   ```

2. **Load Media Files:**

   - Click on **"Add Files"** to select video or image files.
   - The selected files will appear in the list.

3. **Select Output Directory:**

   - Click on **"Select Output Folder"** to choose where the processed files will be saved.

4. **Configure Settings:**

   - Choose the desired resolution (1080p, 2K, or 4K).
   - Select the interpolation method (Nearest, Linear, Cubic, Lanczos).

5. **Start Processing:**

   - Click **"Start Batch Processing"**.
   - A progress bar and status updates will provide real-time feedback.

6. **Completion:**

   - Upon successful completion, a success message will appear with the output folder location.

---

## Examples

![Screenshot](https://github.com/user-attachments/assets/2e222ad2-66da-4e26-9676-f59b4c5cf375)

### Upscaling a Video to 1080p

1. **Input:** A 720p video file (e.g., `sample_video.mp4`).
2. **Settings:** Choose **1080p** resolution and **Cubic** interpolation.
3. **Process:** The application reads the video, upscales each frame, processes the audio, and saves the output as `sample_video_upscaled.mp4` in the selected directory.
4. **Output:** The video is now in 1080p with enhanced clarity and maintained audio synchronization.

### Upscaling an Image to 2K

1. **Input:** A low-resolution image file (e.g., `sample_image.jpg`).
2. **Settings:** Choose **2K** resolution and **Lanczos** interpolation.
3. **Process:** The application resizes the image while preserving detail.
4. **Output:** The resulting file, `sample_image_upscaled.jpg`, is saved in the chosen output directory with improved resolution and image quality.

---

## Contributing

Contributions are welcome! If you wish to contribute to SSUpscaler, please follow these guidelines:

1. **Fork the Repository:** Create your own fork and clone it locally.
2. **Create a Branch:** Use a descriptive branch name (e.g., `feature/new-interpolation-method`).
3. **Commit Changes:** Follow a consistent commit message style and document your changes.
4. **Push and Create a Pull Request:** Submit a PR with a detailed description of your changes and why they improve the project.
5. **Follow Coding Standards:** Ensure your code adheres to the existing style and that tests pass before submission.

For major changes, please open an issue first to discuss your ideas.

---

## License

This project is licensed under the [MIT License](LICENSE). Feel free to use, modify, and distribute this software as long as you adhere to the terms of the license.

---

For further information or support, please feel free to open an issue or contact the project maintainers.
