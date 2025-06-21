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

# ================================================================================================
# STANDARD LIBRARY IMPORTS
# ================================================================================================
import sys
import os
import subprocess
import threading
import time
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil
import tempfile

# ================================================================================================
# THIRD-PARTY LIBRARY IMPORTS - PyQt6 GUI Framework
# ================================================================================================
from PyQt6.QtWidgets import (
    # Main application components
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    # User interface controls
    QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog,
    QComboBox, QSpinBox, QCheckBox, QTabWidget, QGroupBox,
    # List and layout widgets
    QListWidget, QListWidgetItem, QSplitter, QFrame, QGridLayout,
    QSlider, QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import (
    # Threading and signals
    QThread, QObject, pyqtSignal, QTimer, QThreadPool, QRunnable,
    # Core functionality
    Qt, QSize, QSettings, QStandardPaths
)
from PyQt6.QtGui import (
    # Graphics and styling
    QIcon, QPixmap, QFont, QPalette, QColor, QDragEnterEvent,
    QDropEvent, QAction, QKeySequence
)


# ================================================================================================
# WORKER THREAD COMPONENTS
# ================================================================================================

class WorkerSignals(QObject):
    """
    Custom signal class for worker thread communication.

    Provides a clean interface for worker threads to communicate with the main GUI thread.
    All signals are thread-safe and allow for real-time progress updates and error handling.
    """
    # Signal emitted when worker completes successfully
    finished = pyqtSignal()

    # Signal emitted when an error occurs (includes error message)
    error = pyqtSignal(str)

    # Signal emitted to return processing results
    result = pyqtSignal(object)

    # Signal emitted to update progress bars (0-100 integer)
    progress = pyqtSignal(int)

    # Signal emitted to add messages to the application log
    log = pyqtSignal(str)


class UpscaleWorker(QRunnable):
    """
    Multi-threaded worker class for handling image and video upscaling operations.

    This class runs in a separate thread to prevent the GUI from freezing during
    intensive upscaling operations. It handles both image and video processing
    using Real-ESRGAN models with comprehensive error handling and progress reporting.

    Attributes:
        file_path (str): Input file path to be processed
        output_path (str): Destination path for upscaled file
        settings (Dict): Configuration dictionary with model and performance settings
        signals (WorkerSignals): Communication interface with main thread
        is_cancelled (bool): Flag for graceful cancellation
        current_process (subprocess.Popen): Reference to running subprocess for cancellation
    """

    def __init__(self, file_path: str, output_path: str, settings: Dict[str, Any]):
        """
        Initialize the upscale worker with file paths and processing settings.

        Args:
            file_path: Path to the input file (image or video)
            output_path: Path where the upscaled file will be saved
            settings: Dictionary containing processing configuration
        """
        super().__init__()
        self.file_path = file_path
        self.output_path = output_path
        self.settings = settings
        self.signals = WorkerSignals()
        self.is_cancelled = False
        self.current_process = None

    def run(self):
        """
        Main execution method for the worker thread.

        Automatically determines file type and routes to appropriate processing method.
        Includes comprehensive error handling and cleanup.
        """
        try:
            # Determine file type based on extension and route to appropriate handler
            if self.file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv')):
                self._upscale_video()
            else:
                self._upscale_image()
        except Exception as e:
            # Emit error signal with detailed error message
            self.signals.error.emit(str(e))
        finally:
            # Always emit finished signal for proper cleanup
            self.signals.finished.emit()

    def _upscale_image(self):
        """
        Process a single image file using Real-ESRGAN.

        This method handles the complete image upscaling pipeline:
        1. Validates Real-ESRGAN installation and models
        2. Configures processing parameters
        3. Executes upscaling command
        4. Handles errors and reports progress

        Raises:
            FileNotFoundError: If Real-ESRGAN executable or models are missing
            RuntimeError: If the upscaling process fails
        """
        try:
            # Step 1: Locate Real-ESRGAN executable
            realesrgan_path = self._find_realesrgan_executable()
            if not realesrgan_path:
                raise FileNotFoundError("Real-ESRGAN executable not found. Please install Real-ESRGAN.")

            # Step 2: Validate models directory exists
            models_dir = self._find_models_directory(realesrgan_path)
            if not models_dir:
                raise FileNotFoundError("Real-ESRGAN models directory not found. Please ensure models are installed.")

            # Step 3: Validate and configure AI model
            model_name = self.settings.get('model', 'realesr-animevideov3-x2')
            model_file = os.path.join(models_dir, f"{model_name}.param")

            if not os.path.exists(model_file):
                # Fallback mechanism: try to find alternative models
                available_models = self._get_available_models(models_dir)
                if available_models:
                    # Prefer requested model if available, otherwise use first available
                    requested_model = self.settings.get('model', 'realesr-animevideov3-x2')
                    if requested_model in available_models:
                        model_name = requested_model
                    else:
                        model_name = available_models[0]
                    self.signals.log.emit(
                        f"Model '{self.settings.get('model')}' not found, using '{model_name}' instead")
                else:
                    raise FileNotFoundError(f"No Real-ESRGAN models found in {models_dir}")

            # Step 4: Build command line arguments for Real-ESRGAN
            cmd = [
                realesrgan_path,
                '-i', self.file_path,              # Input file
                '-o', self.output_path,            # Output file
                '-n', model_name,                  # AI model name
                '-f', self.settings.get('format', 'jpg')  # Output format
            ]

            # Step 5: Add optional GPU acceleration
            if self.settings.get('use_gpu', True):
                cmd.extend(['-g', '0'])  # Use GPU device 0

            # Step 6: Add tile size for memory management (prevents GPU OOM)
            if self.settings.get('tile_size'):
                cmd.extend(['-t', str(self.settings['tile_size'])])

            # Step 7: Log processing start and command details
            self.signals.log.emit(f"Processing: {os.path.basename(self.file_path)}")
            self.signals.log.emit(f"Command: {' '.join(cmd)}")

            # Step 8: Execute Real-ESRGAN process
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                # Hide console window on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Wait for process completion and capture output
            stdout, stderr = self.current_process.communicate()
            process = self.current_process  # Maintain reference for compatibility

            # Step 9: Check for processing errors
            if process.returncode != 0:
                raise RuntimeError(f"Upscaling failed: {stderr}")

            # Step 10: Report successful completion
            self.signals.log.emit(f"✓ Completed: {os.path.basename(self.output_path)}")
            self.signals.result.emit(self.output_path)

        except Exception as e:
            # Comprehensive error handling with context
            self.signals.error.emit(f"Image upscaling error: {str(e)}")

    def _find_models_directory(self, realesrgan_path: str) -> Optional[str]:
        """
        Locate the Real-ESRGAN models directory using multiple search strategies.

        Searches in common locations relative to the executable and current directory.

        Args:
            realesrgan_path: Path to the Real-ESRGAN executable

        Returns:
            Path to models directory if found, None otherwise
        """
        # Get directory containing the executable
        exe_dir = os.path.dirname(realesrgan_path)

        # Define potential model directory locations in order of preference
        possible_dirs = [
            os.path.join(exe_dir, 'models'),           # Same directory as executable
            os.path.join(exe_dir, '..', 'models'),     # Parent directory
            os.path.join(os.getcwd(), 'models'),       # Current working directory
            os.path.join(os.getcwd(), 'bin', 'models') # Bin subdirectory
        ]

        # Search for valid models directory
        for models_dir in possible_dirs:
            if os.path.exists(models_dir) and os.path.isdir(models_dir):
                return models_dir

        return None

    def _get_available_models(self, models_dir: str) -> List[str]:
        """
        Scan models directory and return list of valid Real-ESRGAN models.

        A valid model requires both .param and .bin files with matching names.

        Args:
            models_dir: Path to the models directory

        Returns:
            List of available model names (without file extensions)
        """
        if not os.path.exists(models_dir):
            return []

        models = []
        for file in os.listdir(models_dir):
            if file.endswith('.param'):
                model_name = file.replace('.param', '')
                # Verify corresponding .bin file exists
                bin_file = os.path.join(models_dir, f"{model_name}.bin")
                if os.path.exists(bin_file):
                    models.append(model_name)

        return models

    def _upscale_video(self):
        """
        Process video files using frame-by-frame upscaling approach.

        Video upscaling pipeline:
        1. Extract individual frames from source video
        2. Upscale each frame using Real-ESRGAN
        3. Reassemble frames into final video with original audio
        4. Clean up temporary files

        This approach ensures maximum quality but requires significant disk space
        and processing time for longer videos.

        Raises:
            RuntimeError: If any step in the video processing pipeline fails
        """
        try:
            # Step 1: Create secure temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix='anime_upscaler_')
            frames_dir = os.path.join(temp_dir, 'frames')
            upscaled_dir = os.path.join(temp_dir, 'upscaled')
            os.makedirs(frames_dir, exist_ok=True)
            os.makedirs(upscaled_dir, exist_ok=True)

            try:
                # Step 2: Extract all frames from source video
                self.signals.log.emit("Extracting video frames...")
                self._extract_frames(self.file_path, frames_dir)

                # Check for user cancellation
                if self.is_cancelled:
                    return

                # Step 3: Upscale each extracted frame
                self.signals.log.emit("Upscaling frames...")
                self._upscale_frames(frames_dir, upscaled_dir)

                # Check for user cancellation
                if self.is_cancelled:
                    return

                # Step 4: Reassemble upscaled frames into final video
                self.signals.log.emit("Reassembling video...")
                self._reassemble_video(upscaled_dir, self.output_path, self.file_path)

                # Step 5: Report successful completion
                self.signals.log.emit(f"✓ Video upscaling completed: {os.path.basename(self.output_path)}")
                self.signals.result.emit(self.output_path)

            finally:
                # Step 6: Always clean up temporary files (even on failure/cancellation)
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.signals.log.emit(f"Warning: Could not clean up temporary files: {str(e)}")

        except Exception as e:
            # Comprehensive error handling for video processing
            self.signals.error.emit(f"Video upscaling error: {str(e)}")

    def _extract_frames(self, video_path: str, frames_dir: str):
        """
        Extract individual frames from video using FFmpeg.

        Uses high-quality settings to preserve image fidelity for upscaling.

        Args:
            video_path: Path to source video file
            frames_dir: Directory to store extracted frames

        Raises:
            RuntimeError: If frame extraction fails
        """
        ffmpeg_path = self._get_ffmpeg_path()

        # Build FFmpeg command for high-quality frame extraction
        cmd = [
            ffmpeg_path,
            '-i', video_path,                      # Input video
            '-q:v', '1',                          # Highest quality (1-31, lower = better)
            '-pix_fmt', 'rgb24',                  # RGB color format for compatibility
            os.path.join(frames_dir, 'frame_%06d.png')  # Output pattern with zero-padding
        ]

        # Execute frame extraction
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if process.returncode != 0:
            raise RuntimeError(f"Frame extraction failed: {process.stderr}")

    def _upscale_frames(self, frames_dir: str, upscaled_dir: str):
        """
        Upscale all extracted frames using Real-ESRGAN.

        Processes frames sequentially with progress reporting. Handles individual
        frame failures gracefully to avoid stopping the entire video processing.

        Args:
            frames_dir: Directory containing extracted frames
            upscaled_dir: Directory for upscaled frames

        Raises:
            RuntimeError: If no frames are found to process
        """
        # Get sorted list of frame files
        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
        if not frame_files:
            raise RuntimeError("No frames were extracted from the video")

        total_frames = len(frame_files)

        # Locate Real-ESRGAN executable
        realesrgan_path = self._find_realesrgan_executable()
        if not realesrgan_path:
            raise FileNotFoundError("Real-ESRGAN executable not found")

        # Process each frame individually
        for i, frame_file in enumerate(frame_files):
            # Check for user cancellation
            if self.is_cancelled:
                break

            # Define input and output paths for current frame
            input_path = os.path.join(frames_dir, frame_file)
            output_path = os.path.join(upscaled_dir, frame_file)

            # Build Real-ESRGAN command for current frame
            cmd = [
                realesrgan_path,
                '-i', input_path,
                '-o', output_path,
                '-n', self.settings.get('model', 'realesr-animevideov3-x2'),
            ]

            # Add GPU acceleration if enabled
            if self.settings.get('use_gpu', True):
                cmd.extend(['-g', '0'])

            # Add tile size for memory management
            if self.settings.get('tile_size'):
                cmd.extend(['-t', str(self.settings['tile_size'])])

            # Execute upscaling for current frame
            process = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Log individual frame failures but continue processing
            if process.returncode != 0:
                self.signals.log.emit(f"Warning: Frame {frame_file} failed to upscale")

            # Update progress bar
            progress = int((i + 1) / total_frames * 100)
            self.signals.progress.emit(progress)

    def _reassemble_video(self, upscaled_dir: str, output_path: str, original_video: str):
        """
        Reassemble upscaled frames into final video with original audio.

        Preserves original video properties (framerate, audio) while using
        upscaled frames for improved visual quality.

        Args:
            upscaled_dir: Directory containing upscaled frames
            output_path: Path for final output video
            original_video: Path to original video (for audio extraction)

        Raises:
            RuntimeError: If video reassembly fails
        """
        ffmpeg_path = self._get_ffmpeg_path()

        # Step 1: Extract audio from original video
        temp_audio = os.path.join(os.path.dirname(output_path), 'temp_audio.aac')
        audio_cmd = [
            ffmpeg_path,
            '-i', original_video,
            '-vn',                    # No video stream
            '-acodec', 'copy',        # Copy audio without re-encoding
            temp_audio
        ]

        # Execute audio extraction (ignore errors if no audio track exists)
        subprocess.run(
            audio_cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        # Step 2: Reassemble video with upscaled frames and extracted audio
        reassemble_cmd = [
            ffmpeg_path,
            '-framerate', str(self.settings.get('fps', 24)),           # Output framerate
            '-i', os.path.join(upscaled_dir, 'frame_%06d.png'),       # Input frame pattern
            '-i', temp_audio,                                         # Audio track
            '-c:v', 'libx264',                                        # Video codec
            '-c:a', 'aac',                                           # Audio codec
            '-pix_fmt', 'yuv420p',                                   # Pixel format for compatibility
            '-crf', str(self.settings.get('quality', 18)),          # Video quality (0-51, lower = better)
            output_path
        ]

        # Execute video reassembly
        process = subprocess.run(
            reassemble_cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        # Step 3: Clean up temporary audio file
        try:
            os.remove(temp_audio)
        except:
            pass  # Ignore cleanup errors

        # Step 4: Check for reassembly errors
        if process.returncode != 0:
            raise RuntimeError(f"Video reassembly failed: {process.stderr}")

    def _find_realesrgan_executable(self) -> Optional[str]:
        """
        Locate Real-ESRGAN executable using multiple search strategies.

        Searches in local directories first, then system PATH.

        Returns:
            Path to executable if found, None otherwise
        """
        # Common executable names across platforms
        possible_names = [
            'realesrgan-ncnn-vulkan',      # Standard Linux/Mac name
            'realesrgan-ncnn-vulkan.exe',  # Windows name
            'realsr-esrgan',               # Alternative name
            'realsr-esrgan.exe'            # Alternative Windows name
        ]

        # Search in local directories first
        search_paths = ['.', 'bin', os.path.join(os.getcwd(), 'bin')]

        for path in search_paths:
            for name in possible_names:
                full_path = os.path.join(path, name)
                if os.path.isfile(full_path):
                    return full_path

        # Search in system PATH as fallback
        for name in possible_names:
            if shutil.which(name):
                return shutil.which(name)

        return None

    def _get_ffmpeg_path(self) -> str:
        """
        Locate FFmpeg executable for video processing.

        Returns:
            Path to FFmpeg executable

        Raises:
            FileNotFoundError: If FFmpeg is not found
        """
        # Check local bin folder first
        bin_ffmpeg = os.path.join('bin', 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
        if os.path.isfile(bin_ffmpeg):
            return bin_ffmpeg

        # Check system PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path

        raise FileNotFoundError("FFmpeg not found. Please ensure ffmpeg is in the bin folder or in PATH.")

    def cancel(self):
        """
        Gracefully cancel the current upscaling operation.

        Attempts to terminate the running process cleanly, with fallback to force kill.
        Sets cancellation flag to stop frame processing loops.
        """
        self.is_cancelled = True
        if self.current_process:
            try:
                # Try graceful termination first
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            except:
                try:
                    # Force kill if graceful termination fails
                    self.current_process.kill()
                except:
                    pass  # Process may have already ended


# ================================================================================================
# SETTINGS DIALOG COMPONENT
# ================================================================================================

class SettingsDialog(QDialog):
    """
    Advanced settings configuration dialog.

    Provides a comprehensive interface for configuring all upscaling parameters:
    - AI model selection
    - Performance optimization settings
    - Video encoding parameters
    - Output format preferences

    The dialog maintains settings persistence and validates user input.
    """

    def __init__(self, parent=None):
        """
        Initialize the settings dialog with organized control groups.

        Args:
            parent: Parent widget (typically the main window)
        """
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.setModal(True)  # Block interaction with parent until closed
        self.resize(400, 500)

        # Create main layout
        layout = QVBoxLayout(self)

        # ========================================================================================
        # AI MODEL SELECTION GROUP
        # ========================================================================================
        model_group = QGroupBox("AI Model Settings")
        model_layout = QFormLayout(model_group)

        # Model selection dropdown with pre-configured options
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'realesr-animevideov3-x2',    # 2x upscaling, optimized for anime videos
            'realesr-animevideov3-x3',    # 3x upscaling, optimized for anime videos
            'realesr-animevideov3-x4',    # 4x upscaling, optimized for anime videos
            'realesrgan-x4plus',          # 4x upscaling, general purpose
            'realesrgan-x4plus-anime'     # 4x upscaling, anime photos specialization
        ])
        model_layout.addRow("Model:", self.model_combo)

        # ========================================================================================
        # PERFORMANCE OPTIMIZATION GROUP
        # ========================================================================================
        perf_group = QGroupBox("Performance Settings")
        perf_layout = QFormLayout(perf_group)

        # GPU acceleration toggle
        self.gpu_check = QCheckBox("Use GPU Acceleration")
        self.gpu_check.setChecked(True)  # Default to GPU acceleration
        self.gpu_check.setToolTip("Enable GPU processing for faster upscaling (requires compatible graphics card)")
        perf_layout.addRow(self.gpu_check)

        # Tile size for memory management
        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(0, 2048)      # 0 = auto, up to 2048 pixels
        self.tile_spin.setValue(400)          # Conservative default
        self.tile_spin.setSpecialValueText("Auto")  # Display "Auto" for value 0
        self.tile_spin.setToolTip(
            "Controls GPU memory usage:\n"
            "• Lower values (100-200): Less GPU memory, slower processing\n"
            "• Higher values (600-1000): More GPU memory, faster processing\n"
            "• Auto: Let Real-ESRGAN decide based on available memory"
        )
        perf_layout.addRow("Tile Size (GPU Memory):", self.tile_spin)

        # ========================================================================================
        # VIDEO ENCODING SETTINGS GROUP
        # ========================================================================================
        video_group = QGroupBox("Video Processing Settings")
        video_layout = QFormLayout(video_group)

        # Output framerate control
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)        # Support from 1 to 120 FPS
        self.fps_spin.setValue(24)            # Standard cinema framerate
        self.fps_spin.setToolTip("Output video framerate (frames per second)")
        video_layout.addRow("Output FPS:", self.fps_spin)

        # Video quality control (CRF - Constant Rate Factor)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(0, 51)     # H.264 CRF range
        self.quality_spin.setValue(18)        # High quality default
        self.quality_spin.setToolTip(
            "Video quality setting (CRF):\n"
            "• 0-17: Visually lossless (very large files)\n"
            "• 18-23: High quality (recommended)\n"
            "• 24-28: Medium quality\n"
            "• 29+: Lower quality (smaller files)"
        )
        video_layout.addRow("Video Quality (CRF):", self.quality_spin)

        # ========================================================================================
        # OUTPUT FORMAT SETTINGS GROUP
        # ========================================================================================
        output_group = QGroupBox("Output Format Settings")
        output_layout = QFormLayout(output_group)

        # Image output format selection
        self.format_combo = QComboBox()
        self.format_combo.addItems(['jpg', 'png', 'webp'])
        self.format_combo.setToolTip(
            "Output format for images:\n"
            "• JPG: Smaller files, good for photos\n"
            "• PNG: Lossless, larger files, supports transparency\n"
            "• WebP: Modern format, good compression"
        )
        output_layout.addRow("Image Format:", self.format_combo)

        # ========================================================================================
        # DIALOG ASSEMBLY AND CONTROLS
        # ========================================================================================

        # Add all groups to main layout
        layout.addWidget(model_group)
        layout.addWidget(perf_group)
        layout.addWidget(video_group)
        layout.addWidget(output_group)

        # Standard dialog buttons (OK/Cancel)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)  # Close dialog and return Accepted
        buttons.rejected.connect(self.reject)  # Close dialog and return Rejected
        layout.addWidget(buttons)

    def get_settings(self) -> Dict[str, Any]:
        """
        Extract current settings from dialog controls.

        Returns:
            Dictionary containing all current setting values
        """
        return {
            'model': self.model_combo.currentText(),
            'use_gpu': self.gpu_check.isChecked(),
            'tile_size': self.tile_spin.value() if self.tile_spin.value() > 0 else None,
            'fps': self.fps_spin.value(),
            'quality': self.quality_spin.value(),
            'format': self.format_combo.currentText()
        }

    def set_settings(self, settings: Dict[str, Any]):
        """
        Apply settings dictionary to dialog controls.

        Args:
            settings: Dictionary containing setting values to apply
        """
        self.model_combo.setCurrentText(settings.get('model', 'realesr-animevideov3-x2'))
        self.gpu_check.setChecked(settings.get('use_gpu', True))
        self.tile_spin.setValue(settings.get('tile_size', 400) or 0)
        self.fps_spin.setValue(settings.get('fps', 24))
        self.quality_spin.setValue(settings.get('quality', 18))
        self.format_combo.setCurrentText(settings.get('format', 'jpg'))


# ================================================================================================
# MAIN APPLICATION WINDOW
# ================================================================================================

class AnimeUpscalerGUI(QMainWindow):
    """
    Main application window providing the complete user interface.

    Features:
    - Drag-and-drop file management
    - Batch processing queue
    - Real-time progress monitoring
    - Comprehensive logging system
    - Settings persistence
    - Professional modern styling

    The application uses a multi-threaded architecture to ensure the UI remains
    responsive during intensive upscaling operations.
    """

    def __init__(self):
        """
        Initialize the main application window.

        Sets up the UI components, loads saved settings, and performs
        dependency checks to ensure all required tools are available.
        """
        super().__init__()

        # Initialize application settings and threading
        self.settings = QSettings('AnimeUpscaler', 'Settings')
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(2)  # Limit concurrent processes to prevent system overload
        self.current_workers = []  # Track active worker threads
        self.output_folder = None  # Selected output directory

        # Initialize the user interface
        self.init_ui()

        # Load previously saved settings
        self.load_settings()

        # Verify all required dependencies are installed
        self.check_dependencies()

    # ============================================================================================
    # USER INTERFACE INITIALIZATION
    # ============================================================================================

    def init_ui(self):
        """
        Initialize the complete user interface layout.

        Creates a modern, professional interface with:
        - Resizable left/right panels
        - File management controls
        - Progress monitoring
        - Comprehensive logging
        - Menu system with keyboard shortcuts
        """
        # Set window properties
        self.setWindowTitle("Anime-Media-Upscaler")
        self.setGeometry(100, 100, 1200, 800)

        # Set application icon if available
        icon_path = 'favicon.ico'
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Enable drag and drop functionality
        self.setAcceptDrops(True)

        # Create main central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create resizable splitter for flexible panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Initialize left panel (file management and controls)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Initialize right panel (progress monitoring and logs)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Set balanced splitter proportions (50/50 split)
        splitter.setSizes([600, 600])

        # Create comprehensive menu system
        self.create_menu_bar()

        # Initialize status bar
        self.statusBar().showMessage("Ready")

        # Apply modern professional styling
        self.apply_modern_style()

    def create_left_panel(self) -> QWidget:
        """
        Create the left control panel containing file management and processing controls.

        Returns:
            QWidget: Complete left panel with all controls
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # ========================================================================================
        # FILE SELECTION GROUP
        # ========================================================================================
        file_group = QGroupBox("Input Files")
        file_layout = QVBoxLayout(file_group)

        # File list widget with drag-and-drop support
        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.file_list.setAlternatingRowColors(True)  # Improve readability
        file_layout.addWidget(self.file_list)

        # File management buttons
        file_buttons = QHBoxLayout()

        # Add individual files button
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        file_buttons.addWidget(self.add_files_btn)

        # Add entire folder button
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.add_folder)
        file_buttons.addWidget(self.add_folder_btn)

        # Clear all files button
        self.clear_files_btn = QPushButton("Clear All")
        self.clear_files_btn.clicked.connect(self.clear_files)
        file_buttons.addWidget(self.clear_files_btn)

        file_layout.addLayout(file_buttons)
        layout.addWidget(file_group)

        # ========================================================================================
        # OUTPUT SETTINGS GROUP
        # ========================================================================================
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)

        # Output folder selection
        self.output_path_btn = QPushButton("Select Output Folder")
        self.output_path_btn.clicked.connect(self.select_output_folder)
        output_layout.addRow("Output Folder:", self.output_path_btn)

        # Display selected output path
        self.output_path_label = QLabel("Not selected")
        self.output_path_label.setStyleSheet("color: gray;")
        output_layout.addRow("", self.output_path_label)

        layout.addWidget(output_group)

        # ========================================================================================
        # QUICK SETTINGS GROUP
        # ========================================================================================
        quick_group = QGroupBox("Quick Settings")
        quick_layout = QFormLayout(quick_group)

        # Model selection dropdown with user-friendly names
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'Anime Image/Video 2x',
            'Anime Image/Video 3x',
            'Anime Image/Video 4x',
            'General Image/Video 4x',
            'Anime Photos 4x'
        ])
        quick_layout.addRow("Model:", self.model_combo)

        layout.addWidget(quick_group)

        # ========================================================================================
        # CONTROL BUTTONS
        # ========================================================================================
        control_layout = QVBoxLayout()

        # Advanced settings button
        self.settings_btn = QPushButton("Advanced Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        control_layout.addWidget(self.settings_btn)

        # Main start processing button with enhanced styling
        self.start_btn = QPushButton("Start Upscaling")
        self.start_btn.clicked.connect(self.start_upscaling)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_layout.addWidget(self.start_btn)

        # Stop processing button with warning styling
        self.stop_btn = QPushButton("Stop Processing")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_layout.addWidget(self.stop_btn)

        layout.addLayout(control_layout)
        layout.addStretch()  # Push content to top

        return panel

    def create_right_panel(self) -> QWidget:
        """
        Create the right progress monitoring panel.

        Returns:
            QWidget: Complete right panel with progress bars and logging
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # ========================================================================================
        # PROGRESS MONITORING GROUP
        # ========================================================================================
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        # Overall batch progress bar
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(QLabel("Overall Progress:"))
        progress_layout.addWidget(self.overall_progress)

        # Current file progress bar
        self.current_progress = QProgressBar()
        self.current_progress.setTextVisible(True)
        progress_layout.addWidget(QLabel("Current File:"))
        progress_layout.addWidget(self.current_progress)

        # Status and timing information
        self.status_label = QLabel("Ready to start")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        progress_layout.addWidget(self.status_label)

        self.time_label = QLabel("")
        progress_layout.addWidget(self.time_label)

        layout.addWidget(progress_group)

        # ========================================================================================
        # LOGGING GROUP
        # ========================================================================================
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)

        # Main log display with monospace font for better readability
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)

        # Log management buttons
        log_buttons = QHBoxLayout()

        # Clear log button
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_buttons.addWidget(clear_log_btn)

        # Save log to file button
        save_log_btn = QPushButton("Save Log")
        save_log_btn.clicked.connect(self.save_log)
        log_buttons.addWidget(save_log_btn)

        log_buttons.addStretch()
        log_layout.addLayout(log_buttons)

        layout.addWidget(log_group)

        return panel

    def create_menu_bar(self):
        """
        Create comprehensive menu bar with keyboard shortcuts.

        Provides standard menu structure with:
        - File operations
        - Tool access
        - Help and about information
        """
        menubar = self.menuBar()

        # ========================================================================================
        # FILE MENU
        # ========================================================================================
        file_menu = menubar.addMenu('File')

        # Add files with standard keyboard shortcut
        add_files_action = QAction('Add Files...', self)
        add_files_action.setShortcut(QKeySequence.StandardKey.Open)
        add_files_action.triggered.connect(self.add_files)
        file_menu.addAction(add_files_action)

        # Add folder option
        add_folder_action = QAction('Add Folder...', self)
        add_folder_action.triggered.connect(self.add_folder)
        file_menu.addAction(add_folder_action)

        file_menu.addSeparator()

        # Exit application with standard shortcut
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ========================================================================================
        # TOOLS MENU
        # ========================================================================================
        tools_menu = menubar.addMenu('Tools')

        # Settings access
        settings_action = QAction('Settings...', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # ========================================================================================
        # HELP MENU
        # ========================================================================================
        help_menu = menubar.addMenu('Help')

        # About dialog
        about_action = QAction('About...', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def apply_modern_style(self):
        """
        Apply modern dark theme styling for professional appearance.

        Creates a cohesive visual design with:
        - Dark theme for reduced eye strain
        - Consistent color scheme
        - Professional typography
        - Intuitive visual hierarchy
        """
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                selection-background-color: #0078d4;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
        """)

    # ============================================================================================
    # DRAG AND DROP FUNCTIONALITY
    # ============================================================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Handle drag enter events for file dropping.

        Args:
            event: The drag enter event containing file information
        """
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """
        Handle drop events to process dragged files and folders.

        Args:
            event: The drop event containing the dropped files/folders
        """
        files = []

        # Process each dropped item
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()

            if os.path.isfile(file_path):
                # Add individual file
                files.append(file_path)
            elif os.path.isdir(file_path):
                # Add all supported files from directory
                files.extend(self.get_files_from_directory(file_path))

        # Add all collected files to the processing queue
        self.add_files_to_list(files)

    # ============================================================================================
    # FILE MANAGEMENT METHODS
    # ============================================================================================

    def add_files(self):
        """
        Open file dialog to add individual files to the processing queue.

        Supports multiple file selection with comprehensive format filtering.
        """
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images or Videos",
            "",
            "All Supported (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.mp4 *.avi *.mkv *.mov *.wmv *.flv);;"
            "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.webp);;"
            "Videos (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;"
            "All Files (*)"
        )
        self.add_files_to_list(files)

    def add_folder(self):
        """
        Open folder dialog to add all supported files from a directory.

        Recursively searches the selected folder for supported media files.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            files = self.get_files_from_directory(folder)
            self.add_files_to_list(files)

    def get_files_from_directory(self, directory: str) -> List[str]:
        """
        Recursively collect all supported media files from a directory.

        Args:
            directory: Path to the directory to search

        Returns:
            List[str]: List of paths to supported media files
        """
        # Define supported file extensions
        supported_extensions = {
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp',  # Image formats
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'  # Video formats
        }

        files = []

        # Walk through directory tree
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if Path(filename).suffix.lower() in supported_extensions:
                    files.append(os.path.join(root, filename))

        return files

    def add_files_to_list(self, files: List[str]):
        """
        Add files to the processing list widget, avoiding duplicates.

        Args:
            files: List of file paths to add
        """
        added_count = 0

        for file_path in files:
            # Check for existing files to prevent duplicates
            existing_items = [self.file_list.item(i).text()
                              for i in range(self.file_list.count())]

            if file_path not in existing_items:
                item = QListWidgetItem(file_path)
                self.file_list.addItem(item)
                added_count += 1

        if added_count > 0:
            self.log(f"Added {added_count} files to processing queue")

    def clear_files(self):
        """
        Clear all files from the processing queue.
        """
        self.file_list.clear()
        self.log("Cleared all files from queue")

    def select_output_folder(self):
        """
        Open folder dialog to select output directory and save the preference.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_path_label.setText(folder)
            self.output_path_label.setStyleSheet("color: white;")

            # Persist the selection
            self.settings.setValue('output_folder', folder)

    # ============================================================================================
    # SETTINGS MANAGEMENT
    # ============================================================================================

    def show_settings(self):
        """
        Display the advanced settings dialog and apply any changes.
        """
        dialog = SettingsDialog(self)

        # Load current settings into dialog
        current_settings = self.get_current_settings()
        dialog.set_settings(current_settings)

        # Process dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            self.save_advanced_settings(new_settings)

            # Update quick settings combo to match advanced model selection
            model_map_reverse = {
                'realesr-animevideov3-x2': 'Anime Image/Video 2x',
                'realesr-animevideov3-x3': 'Anime Image/Video 3x',
                'realesr-animevideov3-x4': 'Anime Image/Video 4x',
                'realesrgan-x4plus': 'General Image/Video 4x',
                'realesrgan-x4plus-anime': 'Anime Photos 4x'
            }
            quick_model = model_map_reverse.get(new_settings['model'], 'Anime Image/Video 2x')
            self.model_combo.setCurrentText(quick_model)

            self.log("Settings updated")

    def get_current_settings(self) -> Dict[str, Any]:
        """
        Get current application settings, combining UI selections with saved preferences.

        Returns:
            Dict[str, Any]: Current application settings
        """
        # Map user-friendly names to actual model identifiers
        model_map = {
            'Anime Image/Video 2x': 'realesr-animevideov3-x2',
            'Anime Image/Video 3x': 'realesr-animevideov3-x3',
            'Anime Image/Video 4x': 'realesr-animevideov3-x4',
            'General Image/Video 4x': 'realesrgan-x4plus',
            'Anime Photos 4x': 'realesrgan-x4plus-anime'
        }

        return {
            'model': model_map.get(self.model_combo.currentText(), 'realesr-animevideov3-x2'),
            'use_gpu': self.settings.value('advanced_use_gpu', True, bool),
            'tile_size': self.settings.value('advanced_tile_size', 400, int),
            'fps': self.settings.value('advanced_fps', 24, int),
            'quality': self.settings.value('advanced_quality', 18, int),
            'format': self.settings.value('advanced_format', 'jpg', str)
        }

    def save_advanced_settings(self, settings: Dict[str, Any]):
        """
        Save advanced settings to persistent storage.

        Args:
            settings: Dictionary of settings to save
        """
        for key, value in settings.items():
            self.settings.setValue(f'advanced_{key}', value)

        # Force immediate save to disk
        self.settings.sync()

    # ============================================================================================
    # PROCESSING CONTROL METHODS
    # ============================================================================================

    def start_upscaling(self):
        """
        Begin the batch upscaling process with comprehensive validation.

        Performs pre-processing checks and initializes the worker thread system.
        """
        # Validate input files
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Warning", "Please add files to process")
            return

        # Validate output folder selection
        if not self.output_folder:
            QMessageBox.warning(self, "Warning", "Please select an output folder")
            return

        # Verify system dependencies
        if not self.check_dependencies():
            return

        # Initialize progress tracking
        self.overall_progress.setValue(0)
        self.current_progress.setValue(0)
        self.processed_files = 0
        self.total_files = self.file_list.count()
        self.start_time = time.time()

        # Update UI state for processing mode
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Processing...")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

        # Clear any existing worker references
        self.current_workers.clear()

        # Begin processing queue
        self.process_next_file()

        self.log(f"Started processing {self.total_files} files")

    def process_next_file(self):
        """
        Process the next file in the queue using the worker thread system.

        Handles file path generation, output naming, and worker thread creation.
        """
        # Check if all files have been processed
        if self.processed_files >= self.total_files:
            self.processing_completed()
            return

        # Get next file from queue
        file_path = self.file_list.item(self.processed_files).text()

        # Generate appropriate output filename
        file_name = Path(file_path).stem
        file_ext = Path(file_path).suffix

        # Preserve video extensions, use settings for images
        if file_ext.lower() in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
            output_ext = file_ext
        else:
            output_ext = f".{self.get_current_settings()['format']}"

        # Extract scale factor from model name for filename
        model_name = self.get_current_settings()['model']
        scale = 'x4'  # Default scale
        if 'x2' in model_name:
            scale = 'x2'
        elif 'x3' in model_name:
            scale = 'x3'
        elif 'x4' in model_name:
            scale = 'x4'

        # Create descriptive output filename
        output_filename = f"{file_name}_upscaled_{scale}{output_ext}"
        output_path = os.path.join(self.output_folder, output_filename)

        # Create and configure worker thread
        worker = UpscaleWorker(file_path, output_path, self.get_current_settings())

        # Connect worker signals to UI update methods
        worker.signals.finished.connect(self.on_file_finished)
        worker.signals.error.connect(self.on_error)
        worker.signals.progress.connect(self.current_progress.setValue)
        worker.signals.log.connect(self.log)

        # Track active worker and start processing
        self.current_workers.append(worker)
        self.thread_pool.start(worker)

    def on_file_finished(self):
        """
        Handle completion of individual file processing.

        Updates progress tracking and initiates processing of the next file.
        """
        # Remove completed worker from tracking list
        sender = self.sender()
        worker_to_remove = None

        for worker in self.current_workers:
            if worker.signals == sender:
                worker_to_remove = worker
                break

        if worker_to_remove:
            self.current_workers.remove(worker_to_remove)

        # Update progress counters
        self.processed_files += 1

        # Update overall progress bar
        progress = int((self.processed_files / self.total_files) * 100)
        self.overall_progress.setValue(progress)

        # Calculate and display time estimates
        if self.processed_files > 0:
            elapsed = time.time() - self.start_time
            avg_time = elapsed / self.processed_files
            remaining = (self.total_files - self.processed_files) * avg_time

            self.time_label.setText(f"Elapsed: {self.format_time(elapsed)} | "
                                    f"Remaining: {self.format_time(remaining)}")

        # Reset current file progress for next item
        self.current_progress.setValue(0)

        # Continue with next file in queue
        self.process_next_file()

    def on_error(self, error_message: str):
        """
        Handle processing errors gracefully.

        Args:
            error_message: Descriptive error message from worker thread
        """
        self.log(f"❌ Error: {error_message}")
        self.processed_files += 1

        # Continue processing despite errors
        self.process_next_file()

    def processing_completed(self):
        """
        Handle completion of all batch processing operations.

        Updates UI state, displays completion statistics, and shows success notification.
        """
        elapsed = time.time() - self.start_time

        # Reset UI to ready state
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Completed!")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.time_label.setText(f"Total time: {self.format_time(elapsed)}")

        # Log completion with statistics
        self.log(f"✅ Processing completed! Total time: {self.format_time(elapsed)}")

        # Show user-friendly completion notification
        QMessageBox.information(
            self,
            "Processing Complete",
            f"Successfully processed {self.total_files} files in {self.format_time(elapsed)}"
        )

    def stop_processing(self):
        """
        Stop all active processing operations and reset UI state.

        Safely cancels all worker threads and cleans up resources.
        """
        # Cancel all active worker threads
        for worker in self.current_workers:
            worker.cancel()

        # Wait for threads to finish gracefully (5 second timeout)
        self.thread_pool.waitForDone(5000)

        # Reset UI to ready state
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")

        self.log("Processing stopped by user")

    # ============================================================================================
    # UTILITY METHODS
    # ============================================================================================

    def format_time(self, seconds: float) -> str:
        """
        Format time duration in human-readable format.

        Args:
            seconds: Time duration in seconds

        Returns:
            str: Formatted time string (HH:MM:SS or MM:SS)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def log(self, message: str):
        """
        Add timestamped message to the application log.

        Args:
            message: Log message to display
        """
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()

    def save_log(self):
        """
        Save the current log contents to a text file.

        Opens file dialog for user to specify save location.
        """
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "upscaler_log.txt", "Text Files (*.txt)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.log(f"Log saved to: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log: {str(e)}")

    def check_dependencies(self) -> bool:
        """
        Verify that all required external dependencies are available.

        Returns:
            bool: True if all dependencies are found, False otherwise
        """
        errors = []

        # Check FFmpeg availability
        try:
            # Check for FFmpeg in bin directory first
            ffmpeg_path = 'bin/ffmpeg.exe' if os.name == 'nt' else 'bin/ffmpeg'

            if not os.path.isfile(ffmpeg_path):
                # If not found in bin, check system PATH
                if not shutil.which('ffmpeg'):
                    errors.append("FFmpeg not found. Please ensure ffmpeg is in the bin folder or in PATH.")
        except Exception:
            errors.append("FFmpeg check failed")

        # Check Real-ESRGAN availability
        realesrgan_found = False
        possible_names = [
            'realesrgan-ncnn-vulkan',
            'realesrgan-ncnn-vulkan.exe',
            'realsr-esrgan',
            'realsr-esrgan.exe'
        ]

        # Check in local directories first
        for path in ['.', 'bin']:
            for name in possible_names:
                if os.path.isfile(os.path.join(path, name)):
                    realesrgan_found = True
                    break
            if realesrgan_found:
                break

        # If not found locally, check system PATH
        if not realesrgan_found:
            for name in possible_names:
                if shutil.which(name):
                    realesrgan_found = True
                    break

        # Add error if Real-ESRGAN not found
        if not realesrgan_found:
            errors.append("Real-ESRGAN executable not found. Please install Real-ESRGAN.")

        # Display errors if any dependencies are missing
        if errors:
            error_msg = "Missing dependencies:\n\n" + "\n".join(f"• {error}" for error in errors)
            error_msg += "\n\nPlease check the installation instructions."
            QMessageBox.critical(self, "Dependency Error", error_msg)
            return False

        return True

    def show_about(self):
        """
        Display the About dialog with application information.
        """
        QMessageBox.about(
            self,
            "About Anime-Media-Upscaler",
            """
            <h3>Anime-Media-Upscaler v2.0.0</h3>
            <p>Professional anime image and video upscaling application</p>
            <p><b>Features:</b></p>
            <ul>
            <li>Batch processing of images and videos</li>
            <li>Multiple AI models (Real-ESRGAN)</li>
            <li>GPU acceleration support</li>
            <li>Drag and drop interface</li>
            <li>Professional progress tracking</li>
            </ul>
            <p><b>Supported formats:</b></p>
            <p>Images: JPG, PNG, BMP, TIFF, WebP<br>
            Videos: MP4, AVI, MKV, MOV, WMV, FLV</p>
            """
        )

    def load_settings(self):
        """
        Load application settings from persistent storage.
        Restores user preferences and window state.
        """
        # Load previously selected output folder
        output_folder = self.settings.value('output_folder', '')
        if output_folder and os.path.exists(output_folder):
            self.output_folder = output_folder
            self.output_path_label.setText(output_folder)
            self.output_path_label.setStyleSheet("color: white;")
        else:
            # Reset if folder no longer exists
            self.output_folder = None

        # Restore window geometry from previous session
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """
        Handle application close event.
        Saves settings and ensures clean shutdown.

        Args:
            event: The close event object
        """
        # Save current window geometry for next session
        self.settings.setValue('geometry', self.saveGeometry())

        # Stop any running processes before closing
        if self.stop_btn.isEnabled():
            self.stop_processing()

        # Accept the close event
        event.accept()


def main():
    """
    Main application entry point.
    Initializes the QApplication and main window.
    """
    # Create the main application instance
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Anime-Media-Upscaler")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("UKR-PROJECTS")

    # Set application icon if available
    icon_path = 'favicon.ico'
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create and display the main window
    window = AnimeUpscalerGUI()
    window.show()

    # Log application startup information
    window.log("Anime-Media-Upscaler v2.0.0 started")
    window.log("Checking dependencies...")

    # Start the application event loop
    sys.exit(app.exec())


# Application entry point
if __name__ == "__main__":
    main()