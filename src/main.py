"""
Anime Media Upscaler - Professional Anime Image and Video Upscaling Application
==============================================

A PyQt6-based GUI application
Uses Real-ESRGAN models with PyQt6 GUI for batch processing

Author: Ujjwal Nova
Version: 2.0.0
License: MIT

Features:
- 2k, 3k and 4k Image/Video Upscaling
- Multi-threaded downloading
- Professional progress tracking
- Drag and drop interface
- Multiple AI models (Real-ESRGAN)
- GPU acceleration support
- Batch processing of images and videos

Dependencies:
- PyQt6: GUI framework
- realesrgan-ncnn-vulkan.exe: YouTube downloading engine
- FFmpeg: Video processing (external binary)

Usage:
cd src
python main.py

Repository: https://github.com/UKR-PROJECTS/Anime-Media-Upscaler
"""

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

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog,
    QComboBox, QSpinBox, QCheckBox, QTabWidget, QGroupBox,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QGridLayout,
    QSlider, QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import (
    QThread, QObject, pyqtSignal, QTimer, QThreadPool, QRunnable,
    Qt, QSize, QSettings, QStandardPaths
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QFont, QPalette, QColor, QDragEnterEvent,
    QDropEvent, QAction, QKeySequence
)


class WorkerSignals(QObject):
    """Signals for worker threads"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)


class UpscaleWorker(QRunnable):
    """Worker thread for upscaling operations"""

    def __init__(self, file_path: str, output_path: str, settings: Dict[str, Any]):
        super().__init__()
        self.file_path = file_path
        self.output_path = output_path
        self.settings = settings
        self.signals = WorkerSignals()
        self.is_cancelled = False
        self.current_process = None

    def run(self):
        try:
            if self.file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv')):
                self._upscale_video()
            else:
                self._upscale_image()
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

    def _upscale_image(self):
        """Upscale a single image using Real-ESRGAN"""
        try:
            # Check if Real-ESRGAN executable exists
            realesrgan_path = self._find_realesrgan_executable()
            if not realesrgan_path:
                raise FileNotFoundError("Real-ESRGAN executable not found. Please install Real-ESRGAN.")

            # Check if models directory exists
            models_dir = self._find_models_directory(realesrgan_path)
            if not models_dir:
                raise FileNotFoundError("Real-ESRGAN models directory not found. Please ensure models are installed.")

            # Validate model exists
            model_name = self.settings.get('model', 'realesr-animevideov3-x2')
            model_file = os.path.join(models_dir, f"{model_name}.param")
            if not os.path.exists(model_file):
                # Fallback to available models
                available_models = self._get_available_models(models_dir)
                if available_models:
                    # Try to find a model that matches the requested one
                    requested_model = self.settings.get('model', 'realesr-animevideov3-x2')
                    if requested_model in available_models:
                        model_name = requested_model
                    else:
                        model_name = available_models[0]
                    self.signals.log.emit(
                        f"Model '{self.settings.get('model')}' not found, using '{model_name}' instead")
                else:
                    raise FileNotFoundError(f"No Real-ESRGAN models found in {models_dir}")

            # Prepare command
            cmd = [
                realesrgan_path,
                '-i', self.file_path,
                '-o', self.output_path,
                '-n', model_name,
                '-f', self.settings.get('format', 'jpg')
            ]

            # Add GPU settings if available
            if self.settings.get('use_gpu', True):
                cmd.extend(['-g', '0'])

            # Add tile size for memory management
            if self.settings.get('tile_size'):
                cmd.extend(['-t', str(self.settings['tile_size'])])

            self.signals.log.emit(f"Processing: {os.path.basename(self.file_path)}")
            self.signals.log.emit(f"Command: {' '.join(cmd)}")

            # Execute command
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            stdout, stderr = self.current_process.communicate()
            process = self.current_process  # For backward compatibility

            if process.returncode != 0:
                raise RuntimeError(f"Upscaling failed: {stderr}")

            self.signals.log.emit(f"✓ Completed: {os.path.basename(self.output_path)}")
            self.signals.result.emit(self.output_path)

        except Exception as e:
            self.signals.error.emit(f"Image upscaling error: {str(e)}")

    def _find_models_directory(self, realesrgan_path: str) -> Optional[str]:
        """Find the models directory for Real-ESRGAN"""
        # Check relative to executable
        exe_dir = os.path.dirname(realesrgan_path)
        possible_dirs = [
            os.path.join(exe_dir, 'models'),
            os.path.join(exe_dir, '..', 'models'),
            os.path.join(os.getcwd(), 'models'),
            os.path.join(os.getcwd(), 'bin', 'models')
        ]

        for models_dir in possible_dirs:
            if os.path.exists(models_dir) and os.path.isdir(models_dir):
                return models_dir

        return None

    def _get_available_models(self, models_dir: str) -> List[str]:
        """Get list of available model names"""
        if not os.path.exists(models_dir):
            return []

        models = []
        for file in os.listdir(models_dir):
            if file.endswith('.param'):
                model_name = file.replace('.param', '')
                # Check if corresponding .bin file exists
                bin_file = os.path.join(models_dir, f"{model_name}.bin")
                if os.path.exists(bin_file):
                    models.append(model_name)

        return models

    def _upscale_video(self):
        """Upscale video by extracting frames, upscaling, and reassembling"""
        try:
            temp_dir = tempfile.mkdtemp(prefix='anime_upscaler_')
            frames_dir = os.path.join(temp_dir, 'frames')
            upscaled_dir = os.path.join(temp_dir, 'upscaled')
            os.makedirs(frames_dir, exist_ok=True)
            os.makedirs(upscaled_dir, exist_ok=True)

            try:
                # Step 1: Extract frames
                self.signals.log.emit("Extracting video frames...")
                self._extract_frames(self.file_path, frames_dir)

                if self.is_cancelled:
                    return

                # Step 2: Upscale frames
                self.signals.log.emit("Upscaling frames...")
                self._upscale_frames(frames_dir, upscaled_dir)

                if self.is_cancelled:
                    return

                # Step 3: Reassemble video
                self.signals.log.emit("Reassembling video...")
                self._reassemble_video(upscaled_dir, self.output_path, self.file_path)

                self.signals.log.emit(f"✓ Video upscaling completed: {os.path.basename(self.output_path)}")
                self.signals.result.emit(self.output_path)


            finally:
                # Clean up temporary files
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.signals.log.emit(f"Warning: Could not clean up temporary files: {str(e)}")

        except Exception as e:
            self.signals.error.emit(f"Video upscaling error: {str(e)}")

    def _extract_frames(self, video_path: str, frames_dir: str):
        """Extract frames from video using ffmpeg"""
        ffmpeg_path = self._get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-q:v', '1',  # High quality
            '-pix_fmt', 'rgb24',
            os.path.join(frames_dir, 'frame_%06d.png')
        ]

        process = subprocess.run(cmd, capture_output=True, text=True,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if process.returncode != 0:
            raise RuntimeError(f"Frame extraction failed: {process.stderr}")

    def _upscale_frames(self, frames_dir: str, upscaled_dir: str):
        """Upscale all frames in directory"""
        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
        if not frame_files:  # Add this check
            raise RuntimeError("No frames were extracted from the video")
        total_frames = len(frame_files)
        total_frames = len(frame_files)

        realesrgan_path = self._find_realesrgan_executable()
        if not realesrgan_path:
            raise FileNotFoundError("Real-ESRGAN executable not found")

        for i, frame_file in enumerate(frame_files):
            if self.is_cancelled:
                break

            input_path = os.path.join(frames_dir, frame_file)
            output_path = os.path.join(upscaled_dir, frame_file)

            cmd = [
                realesrgan_path,
                '-i', input_path,
                '-o', output_path,
                '-n', self.settings.get('model', 'realesr-animevideov3-x2'),
            ]

            if self.settings.get('use_gpu', True):
                cmd.extend(['-g', '0'])

            if self.settings.get('tile_size'):
                cmd.extend(['-t', str(self.settings['tile_size'])])

            process = subprocess.run(cmd, capture_output=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if process.returncode != 0:
                self.signals.log.emit(f"Warning: Frame {frame_file} failed to upscale")

            progress = int((i + 1) / total_frames * 100)
            self.signals.progress.emit(progress)

    def _reassemble_video(self, upscaled_dir: str, output_path: str, original_video: str):
        """Reassemble upscaled frames into video"""
        ffmpeg_path = self._get_ffmpeg_path()

        # Get original video properties
        probe_cmd = [
            ffmpeg_path,
            '-i', original_video,
            '-hide_banner'
        ]

        probe_process = subprocess.run(probe_cmd, capture_output=True, text=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        # Extract audio from original video
        temp_audio = os.path.join(os.path.dirname(output_path), 'temp_audio.aac')
        audio_cmd = [
            ffmpeg_path,
            '-i', original_video,
            '-vn', '-acodec', 'copy',
            temp_audio
        ]

        subprocess.run(audio_cmd, capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        # Reassemble video with audio
        reassemble_cmd = [
            ffmpeg_path,
            '-framerate', str(self.settings.get('fps', 24)),
            '-i', os.path.join(upscaled_dir, 'frame_%06d.png'),
            '-i', temp_audio,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-pix_fmt', 'yuv420p',
            '-crf', str(self.settings.get('quality', 18)),
            output_path
        ]

        process = subprocess.run(reassemble_cmd, capture_output=True, text=True,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        # Clean up temp audio
        try:
            os.remove(temp_audio)
        except:
            pass

        if process.returncode != 0:
            raise RuntimeError(f"Video reassembly failed: {process.stderr}")

    def _find_realesrgan_executable(self) -> Optional[str]:
        """Find Real-ESRGAN executable"""
        possible_names = [
            'realesrgan-ncnn-vulkan',
            'realesrgan-ncnn-vulkan.exe',
            'realsr-esrgan',
            'realsr-esrgan.exe'
        ]

        # Check in current directory and bin folder
        search_paths = ['.', 'bin', os.path.join(os.getcwd(), 'bin')]

        for path in search_paths:
            for name in possible_names:
                full_path = os.path.join(path, name)
                if os.path.isfile(full_path):
                    return full_path

        # Check in PATH
        for name in possible_names:
            if shutil.which(name):
                return shutil.which(name)

        return None

    def _get_ffmpeg_path(self) -> str:
        """Get ffmpeg executable path"""
        # Check bin folder first
        bin_ffmpeg = os.path.join('bin', 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
        if os.path.isfile(bin_ffmpeg):
            return bin_ffmpeg

        # Check in PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path

        raise FileNotFoundError("FFmpeg not found. Please ensure ffmpeg is in the bin folder or in PATH.")

    def cancel(self):
        """Cancel the current operation"""
        self.is_cancelled = True
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            except:
                try:
                    self.current_process.kill()
                except:
                    pass


class SettingsDialog(QDialog):
    """Settings configuration dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 500)

        layout = QVBoxLayout(self)

        # Model settings
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'realesr-animevideov3-x2',
            'realesr-animevideov3-x3',
            'realesr-animevideov3-x4',
            'realesrgan-x4plus',
            'realesrgan-x4plus-anime'
        ])
        model_layout.addRow("Model:", self.model_combo)

        # Performance settings
        perf_group = QGroupBox("Performance Settings")
        perf_layout = QFormLayout(perf_group)

        self.gpu_check = QCheckBox("Use GPU Acceleration")
        self.gpu_check.setChecked(True)
        perf_layout.addRow(self.gpu_check)

        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(0, 2048)
        self.tile_spin.setValue(400)
        self.tile_spin.setSpecialValueText("Auto")
        self.tile_spin.setToolTip(
            "Lower values use less GPU memory but are slower. Higher values are faster but need more GPU memory.")
        perf_layout.addRow("Tile Size (GPU Memory):", self.tile_spin)

        # Video settings
        video_group = QGroupBox("Video Settings")
        video_layout = QFormLayout(video_group)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(24)
        video_layout.addRow("Output FPS:", self.fps_spin)

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(0, 51)
        self.quality_spin.setValue(18)
        video_layout.addRow("Video Quality (CRF):", self.quality_spin)

        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(['jpg', 'png', 'webp'])
        output_layout.addRow("Image Format:", self.format_combo)

        # Add groups to layout
        layout.addWidget(model_group)
        layout.addWidget(perf_group)
        layout.addWidget(video_group)
        layout.addWidget(output_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self) -> Dict[str, Any]:
        """Get current settings"""
        return {
            'model': self.model_combo.currentText(),
            'use_gpu': self.gpu_check.isChecked(),
            'tile_size': self.tile_spin.value() if self.tile_spin.value() > 0 else None,
            'fps': self.fps_spin.value(),
            'quality': self.quality_spin.value(),
            'format': self.format_combo.currentText()
        }

    def set_settings(self, settings: Dict[str, Any]):
        """Set settings from dictionary"""
        self.model_combo.setCurrentText(settings.get('model', 'realesr-animevideov3-x2'))
        self.gpu_check.setChecked(settings.get('use_gpu', True))
        self.tile_spin.setValue(settings.get('tile_size', 400) or 0)
        self.fps_spin.setValue(settings.get('fps', 24))
        self.quality_spin.setValue(settings.get('quality', 18))
        self.format_combo.setCurrentText(settings.get('format', 'jpg'))


class AnimeUpscalerGUI(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings('AnimeUpscaler', 'Settings')
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(2)  # Limit concurrent processes
        self.current_workers = []
        self.output_folder = None

        self.init_ui()
        self.load_settings()
        self.check_dependencies()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Anime-Media-Upscaler")
        self.setGeometry(100, 100, 1200, 800)

        # Set application icon
        icon_path = 'favicon.ico'
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - File management and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel - Progress and logs
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions
        splitter.setSizes([600, 600])

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.statusBar().showMessage("Ready")

        # Apply modern styling
        self.apply_modern_style()

    def create_left_panel(self) -> QWidget:
        """Create the left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # File selection group
        file_group = QGroupBox("Input Files")
        file_layout = QVBoxLayout(file_group)

        # File list
        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.file_list.setAlternatingRowColors(True)
        file_layout.addWidget(self.file_list)

        # File control buttons
        file_buttons = QHBoxLayout()

        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        file_buttons.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.add_folder)
        file_buttons.addWidget(self.add_folder_btn)

        self.clear_files_btn = QPushButton("Clear All")
        self.clear_files_btn.clicked.connect(self.clear_files)
        file_buttons.addWidget(self.clear_files_btn)

        file_layout.addLayout(file_buttons)
        layout.addWidget(file_group)

        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)

        self.output_path_btn = QPushButton("Select Output Folder")
        self.output_path_btn.clicked.connect(self.select_output_folder)
        output_layout.addRow("Output Folder:", self.output_path_btn)

        self.output_path_label = QLabel("Not selected")
        self.output_path_label.setStyleSheet("color: gray;")
        output_layout.addRow("", self.output_path_label)

        layout.addWidget(output_group)

        # Quick settings group
        quick_group = QGroupBox("Quick Settings")
        quick_layout = QFormLayout(quick_group)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'Anime Image/Video 2x',
            'Anime Image/Video 3x',
            'Anime Image/Video 4x',
            'Genera Image/Video 4x',
            'Anime Photos 4x'
        ])
        quick_layout.addRow("Model:", self.model_combo)

        layout.addWidget(quick_group)

        # Control buttons
        control_layout = QVBoxLayout()

        self.settings_btn = QPushButton("Advanced Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        control_layout.addWidget(self.settings_btn)

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
        layout.addStretch()

        return panel

    def create_right_panel(self) -> QWidget:
        """Create the right progress panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(QLabel("Overall Progress:"))
        progress_layout.addWidget(self.overall_progress)

        # Current file progress
        self.current_progress = QProgressBar()
        self.current_progress.setTextVisible(True)
        progress_layout.addWidget(QLabel("Current File:"))
        progress_layout.addWidget(self.current_progress)

        # Status labels
        self.status_label = QLabel("Ready to start")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        progress_layout.addWidget(self.status_label)

        self.time_label = QLabel("")
        progress_layout.addWidget(self.time_label)

        layout.addWidget(progress_group)

        # Log group
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)

        # Log control buttons
        log_buttons = QHBoxLayout()

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_buttons.addWidget(clear_log_btn)

        save_log_btn = QPushButton("Save Log")
        save_log_btn.clicked.connect(self.save_log)
        log_buttons.addWidget(save_log_btn)

        log_buttons.addStretch()
        log_layout.addLayout(log_buttons)

        layout.addWidget(log_group)

        return panel

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        add_files_action = QAction('Add Files...', self)
        add_files_action.setShortcut(QKeySequence.StandardKey.Open)
        add_files_action.triggered.connect(self.add_files)
        file_menu.addAction(add_files_action)

        add_folder_action = QAction('Add Folder...', self)
        add_folder_action.triggered.connect(self.add_folder)
        file_menu.addAction(add_folder_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')

        settings_action = QAction('Settings...', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = QAction('About...', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def apply_modern_style(self):
        """Apply modern dark theme styling"""
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

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                files.append(file_path)
            elif os.path.isdir(file_path):
                files.extend(self.get_files_from_directory(file_path))

        self.add_files_to_list(files)

    def add_files(self):
        """Add files to processing list"""
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
        """Add all supported files from a folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            files = self.get_files_from_directory(folder)
            self.add_files_to_list(files)

    def get_files_from_directory(self, directory: str) -> List[str]:
        """Get all supported files from directory"""
        supported_extensions = {
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp',
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'
        }

        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if Path(filename).suffix.lower() in supported_extensions:
                    files.append(os.path.join(root, filename))

        return files

    def add_files_to_list(self, files: List[str]):
        """Add files to the processing list widget"""
        for file_path in files:
            # Check if file already exists in list
            existing_items = [self.file_list.item(i).text()
                              for i in range(self.file_list.count())]
            if file_path not in existing_items:
                item = QListWidgetItem(file_path)
                self.file_list.addItem(item)

        self.log(f"Added {len(files)} files to processing queue")

    def clear_files(self):
        """Clear all files from the list"""
        self.file_list.clear()
        self.log("Cleared all files from queue")

    def select_output_folder(self):
        """Select output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_path_label.setText(folder)
            self.output_path_label.setStyleSheet("color: white;")
            self.settings.setValue('output_folder', folder)

    def show_settings(self):
        """Show advanced settings dialog"""
        dialog = SettingsDialog(self)

        # Load current settings
        current_settings = self.get_current_settings()
        dialog.set_settings(current_settings)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            self.save_advanced_settings(new_settings)

            # Update quick settings combo box to match advanced model selection
            model_map_reverse = {
                'realesr-animevideov3-x2': 'Anime Anime Image/Video 2x',
                'realesr-animevideov3-x3': 'Anime Anime Image/Video 3x',
                'realesr-animevideov3-x4': 'Anime Anime Image/Video 4x',
                'realesrgan-x4plus': 'General Image/Video 4x',
                'realesrgan-x4plus-anime': 'Anime Photos 4x'
            }
            quick_model = model_map_reverse.get(new_settings['model'], 'Anime Image/Video 2x')
            self.model_combo.setCurrentText(quick_model)

            self.log("Settings updated")

    def get_current_settings(self) -> Dict[str, Any]:
        """Get current application settings"""
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
        """Save advanced settings"""
        for key, value in settings.items():
            self.settings.setValue(f'advanced_{key}', value)
        self.settings.sync()  # Force save to disk

    def start_upscaling(self):
        """Start the upscaling process"""
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Warning", "Please add files to process")
            return

        if not self.output_folder:
            QMessageBox.warning(self, "Warning", "Please select an output folder")
            return

        # Check dependencies
        if not self.check_dependencies():
            return

        # Reset progress
        self.overall_progress.setValue(0)
        self.current_progress.setValue(0)
        self.processed_files = 0
        self.total_files = self.file_list.count()
        self.start_time = time.time()

        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Processing...")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

        # Clear current workers
        self.current_workers.clear()

        # Start processing files
        self.process_next_file()

        self.log(f"Started processing {self.total_files} files")

    def process_next_file(self):
        """Process the next file in the queue"""
        if self.processed_files >= self.total_files:
            self.processing_completed()
            return

        # Get next file
        file_path = self.file_list.item(self.processed_files).text()

        # Generate output filename
        file_name = Path(file_path).stem
        file_ext = Path(file_path).suffix

        # For videos, keep original extension; for images, use settings
        if file_ext.lower() in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
            output_ext = file_ext
        else:
            output_ext = f".{self.get_current_settings()['format']}"

        model_name = self.get_current_settings()['model']
        # Extract scale from model name (e.g., x2, x3, x4)
        scale = 'x4'  # default
        if 'x2' in model_name:
            scale = 'x2'
        elif 'x3' in model_name:
            scale = 'x3'
        elif 'x4' in model_name:
            scale = 'x4'

        output_filename = f"{file_name}_upscaled_{scale}{output_ext}"
        output_path = os.path.join(self.output_folder, output_filename)

        # Create worker
        worker = UpscaleWorker(file_path, output_path, self.get_current_settings())
        worker.signals.finished.connect(self.on_file_finished)
        worker.signals.error.connect(self.on_error)
        worker.signals.progress.connect(self.current_progress.setValue)
        worker.signals.log.connect(self.log)

        self.current_workers.append(worker)
        self.thread_pool.start(worker)

    def on_file_finished(self):
        # Remove finished worker
        sender = self.sender()
        worker_to_remove = None
        for worker in self.current_workers:
            if worker.signals == sender:
                worker_to_remove = worker
                break
        if worker_to_remove:
            self.current_workers.remove(worker_to_remove)

        self.processed_files += 1

        # Update overall progress
        progress = int((self.processed_files / self.total_files) * 100)
        self.overall_progress.setValue(progress)

        # Update time estimate
        if self.processed_files > 0:
            elapsed = time.time() - self.start_time
            avg_time = elapsed / self.processed_files
            remaining = (self.total_files - self.processed_files) * avg_time
            self.time_label.setText(f"Elapsed: {self.format_time(elapsed)} | "
                                    f"Remaining: {self.format_time(remaining)}")

        # Reset current progress
        self.current_progress.setValue(0)

        # Process next file
        self.process_next_file()

    def on_error(self, error_message: str):
        """Handle processing errors"""
        self.log(f"❌ Error: {error_message}")
        self.processed_files += 1

        # Continue with next file
        self.process_next_file()

    def processing_completed(self):
        """Handle completion of all processing"""
        elapsed = time.time() - self.start_time

        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Completed!")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.time_label.setText(f"Total time: {self.format_time(elapsed)}")

        self.log(f"✅ Processing completed! Total time: {self.format_time(elapsed)}")

        # Show completion message
        QMessageBox.information(
            self,
            "Processing Complete",
            f"Successfully processed {self.total_files} files in {self.format_time(elapsed)}"
        )

    def stop_processing(self):
        """Stop all processing"""
        # Cancel all workers
        for worker in self.current_workers:
            worker.cancel()

        # Wait for threads to finish
        self.thread_pool.waitForDone(5000)  # Wait up to 5 seconds

        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")

        self.log("Processing stopped by user")

    def format_time(self, seconds: float) -> str:
        """Format time in human readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def log(self, message: str):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()

    def save_log(self):
        """Save log to file"""
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
        """Check if required dependencies are available"""
        errors = []

        # Check FFmpeg
        try:
            ffmpeg_path = 'bin/ffmpeg.exe' if os.name == 'nt' else 'bin/ffmpeg'
            if not os.path.isfile(ffmpeg_path):
                if not shutil.which('ffmpeg'):
                    errors.append("FFmpeg not found. Please ensure ffmpeg is in the bin folder or in PATH.")
        except:
            errors.append("FFmpeg check failed")

        # Check Real-ESRGAN
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

        if errors:
            error_msg = "Missing dependencies:\n\n" + "\n".join(f"• {error}" for error in errors)
            error_msg += "\n\nPlease check the installation instructions."
            QMessageBox.critical(self, "Dependency Error", error_msg)
            return False

        return True

    def show_about(self):
        """Show about dialog"""
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
        """Load application settings"""
        # Load output folder
        output_folder = self.settings.value('output_folder', '')
        if output_folder and os.path.exists(output_folder):
            self.output_folder = output_folder
            self.output_path_label.setText(output_folder)
            self.output_path_label.setStyleSheet("color: white;")
        else:
            self.output_folder = None

        # Load window geometry
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """Handle application close event"""
        # Save settings
        self.settings.setValue('geometry', self.saveGeometry())

        # Stop any running processes
        if self.stop_btn.isEnabled():
            self.stop_processing()

        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Anime-Media-Upscaler")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("UKR-PROJECTS")

    # Set application icon
    icon_path = 'favicon.ico'
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create and show main window
    window = AnimeUpscalerGUI()
    window.show()

    # Log startup
    window.log("Anime-Media-Upscaler v2.0.0")
    window.log("Checking dependencies...")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()