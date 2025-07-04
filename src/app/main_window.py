"""
This module defines the main application window for the Anime-Media-Upscaler.

It includes the main window class `AnimeUpscalerGUI`, which is responsible for:
- Initializing the user interface (UI) components.
- Handling user interactions, such as adding files, selecting settings, and starting the upscaling process.
- Managing the upscaling process by creating and running worker threads.
- Displaying progress and log information to the user.
- Saving and loading application settings.
"""
import os
import time
from pathlib import Path
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QTextEdit, QFileDialog, QComboBox, QGroupBox,
    QListWidget, QListWidgetItem, QSplitter, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings, QThreadPool
from PyQt6.QtGui import QIcon, QFont, QDragEnterEvent, QDropEvent, QAction, QKeySequence
from .settings_dialog import SettingsDialog
from .workers import UpscaleWorker
from .ui_utils import format_time, get_files_from_directory, check_dependencies

class AnimeUpscalerGUI(QMainWindow):
    """Main application window for the Anime-Media-Upscaler."""

    def __init__(self):
        """Initializes the main window, settings, thread pool, and UI."""
        super().__init__()
        self.settings = QSettings('AnimeUpscaler', 'Settings')
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(2)  # Allow up to 2 concurrent workers
        self.current_workers = []
        self.output_folder = None

        self.init_ui()
        self.load_settings()
        check_dependencies()

    def init_ui(self):
        """Initializes the main user interface components."""
        self.setWindowTitle("Anime-Media-Upscaler")
        self.setGeometry(100, 100, 1200, 800)

        # Set window icon
        icon_path = 'favicon.ico'
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setAcceptDrops(True)  # Enable drag-and-drop

        # Main layout with a splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Add left and right panels to the splitter
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])  # Set initial sizes

        self.create_menu_bar()
        self.statusBar().showMessage("Ready")
        self.apply_modern_style()

    def create_left_panel(self) -> QWidget:
        """Creates the left panel containing input and settings controls."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Input files group
        file_group = QGroupBox("Input Files")
        file_layout = QVBoxLayout(file_group)
        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.file_list.setAlternatingRowColors(True)
        file_layout.addWidget(self.file_list)

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
            'Anime Image/Video 2x', 'Anime Image/Video 3x', 'Anime Image/Video 4x',
            'General Image/Video 4x', 'Anime Photos 4x'
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
                background-color: #4CAF50; color: white; font-weight: bold;
                padding: 10px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        control_layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Stop Processing")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336; color: white; font-weight: bold;
                padding: 10px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #da190b; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        control_layout.addWidget(self.stop_btn)
        layout.addLayout(control_layout)
        layout.addStretch()
        return panel

    def create_right_panel(self) -> QWidget:
        """Creates the right panel containing progress and log information."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(QLabel("Overall Progress:"))
        progress_layout.addWidget(self.overall_progress)
        self.current_progress = QProgressBar()
        self.current_progress.setTextVisible(True)
        progress_layout.addWidget(QLabel("Current File:"))
        progress_layout.addWidget(self.current_progress)
        self.status_label = QLabel("Ready to start")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        progress_layout.addWidget(self.status_label)
        self.time_label = QLabel("")
        progress_layout.addWidget(self.time_label)
        layout.addWidget(progress_group)

        # Processing log group
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
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
        """Creates the application's menu bar."""
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
        """Applies a modern, dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #ffffff; }
            QGroupBox {
                font-weight: bold; border: 2px solid #555555;
                border-radius: 8px; margin-top: 1ex; padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px;
            }
            QListWidget {
                background-color: #3c3c3c; border: 1px solid #555555;
                border-radius: 4px; selection-background-color: #0078d4;
            }
            QPushButton {
                background-color: #404040; border: 1px solid #555555;
                border-radius: 4px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #505050; }
            QPushButton:pressed { background-color: #303030; }
            QComboBox {
                background-color: #404040; border: 1px solid #555555;
                border-radius: 4px; padding: 5px;
            }
            QProgressBar {
                border: 1px solid #555555; border-radius: 4px; text-align: center;
            }
            QProgressBar::chunk { background-color: #0078d4; border-radius: 3px; }
            QTextEdit {
                background-color: #1e1e1e; border: 1px solid #555555;
                border-radius: 4px; color: #ffffff;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handles drag enter events to accept file drops."""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handles drop events to add files to the list."""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                files.append(file_path)
            elif os.path.isdir(file_path):
                files.extend(get_files_from_directory(file_path))
        self.add_files_to_list(files)

    def add_files(self):
        """Opens a dialog to add files to the list."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images or Videos", "",
            "All Supported (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.mp4 *.avi *.mkv *.mov *.wmv *.flv);;"
            "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.webp);;"
            "Videos (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*)"
        )
        self.add_files_to_list(files)

    def add_folder(self):
        """Opens a dialog to add a folder of files to the list."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            files = get_files_from_directory(folder)
            self.add_files_to_list(files)

    def add_files_to_list(self, files):
        """Adds a list of files to the file list widget, avoiding duplicates."""
        added_count = 0
        for file_path in files:
            existing_items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if file_path not in existing_items:
                self.file_list.addItem(QListWidgetItem(file_path))
                added_count += 1
        if added_count > 0:
            self.log(f"Added {added_count} files to processing queue")

    def clear_files(self):
        """Clears all files from the file list."""
        self.file_list.clear()
        self.log("Cleared all files from queue")

    def select_output_folder(self):
        """Opens a dialog to select the output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_path_label.setText(folder)
            self.output_path_label.setStyleSheet("color: white;")
            self.settings.setValue('output_folder', folder)

    def show_settings(self):
        """Shows the advanced settings dialog."""
        dialog = SettingsDialog(self)
        current_settings = self.get_current_settings()
        dialog.set_settings(current_settings)
        if dialog.exec():
            new_settings = dialog.get_settings()
            self.save_advanced_settings(new_settings)
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
        """Returns the current upscaling settings."""
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
        """Saves the advanced settings."""
        for key, value in settings.items():
            self.settings.setValue(f'advanced_{key}', value)
        self.settings.sync()

    def start_upscaling(self):
        """Starts the upscaling process for all files in the list."""
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Warning", "Please add files to process")
            return
        if not self.output_folder:
            QMessageBox.warning(self, "Warning", "Please select an output folder")
            return
        if not check_dependencies():
            return

        # Reset progress and timers
        self.overall_progress.setValue(0)
        self.current_progress.setValue(0)
        self.processed_files = 0
        self.total_files = self.file_list.count()
        self.start_time = time.time()

        # Update UI state
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Processing...")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.current_workers.clear()
        self.process_next_file()
        self.log(f"Started processing {self.total_files} files")

    def process_next_file(self):
        """Processes the next file in the queue."""
        if self.processed_files >= self.total_files:
            self.processing_completed()
            return

        if not self.output_folder:
            self.log("Error: Output folder not set. Aborting.")
            self.stop_processing()
            return

        # Get file details and determine output path
        file_path = self.file_list.item(self.processed_files).text()
        file_name = Path(file_path).stem
        file_ext = Path(file_path).suffix
        if file_ext.lower() in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
            output_ext = file_ext
        else:
            output_ext = f".{self.get_current_settings()['format']}"

        model_name = self.get_current_settings()['model']
        scale = 'x4'
        if 'x2' in model_name: scale = 'x2'
        elif 'x3' in model_name: scale = 'x3'
        elif 'x4' in model_name: scale = 'x4'

        output_filename = f"{file_name}_upscaled_{scale}{output_ext}"
        output_path = os.path.join(self.output_folder, output_filename)

        # Create and start a worker thread
        worker = UpscaleWorker(file_path, output_path, self.get_current_settings())
        worker.signals.finished.connect(self.on_file_finished)
        worker.signals.error.connect(self.on_error)
        worker.signals.progress.connect(self.current_progress.setValue)
        worker.signals.log.connect(self.log)
        self.current_workers.append(worker)
        self.thread_pool.start(worker)

    def on_file_finished(self):
        """Handles the completion of a single file's processing."""
        sender = self.sender()
        worker_to_remove = None
        for worker in self.current_workers:
            if worker.signals == sender:
                worker_to_remove = worker
                break
        if worker_to_remove:
            self.current_workers.remove(worker_to_remove)

        self.processed_files += 1
        progress = int((self.processed_files / self.total_files) * 100)
        self.overall_progress.setValue(progress)

        # Update time estimates
        if self.processed_files > 0:
            elapsed = time.time() - self.start_time
            avg_time = elapsed / self.processed_files
            remaining = (self.total_files - self.processed_files) * avg_time
            self.time_label.setText(f"Elapsed: {format_time(elapsed)} | Remaining: {format_time(remaining)}")

        self.current_progress.setValue(0)
        self.process_next_file()

    def on_error(self, error_message: str):
        """Handles errors reported by worker threads."""
        self.log(f"❌ Error: {error_message}")
        self.processed_files += 1
        self.process_next_file()

    def processing_completed(self):
        """Handles the completion of all processing."""
        elapsed = time.time() - self.start_time
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Completed!")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.time_label.setText(f"Total time: {format_time(elapsed)}")
        self.log(f"✅ Processing completed! Total time: {format_time(elapsed)}")
        QMessageBox.information(
            self, "Processing Complete",
            f"Successfully processed {self.total_files} files in {format_time(elapsed)}"
        )

    def stop_processing(self):
        """Stops all active processing threads."""
        for worker in self.current_workers:
            worker.cancel()
        self.thread_pool.waitForDone(5000)  # Wait up to 5 seconds for threads to finish
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
        self.log("Processing stopped by user")

    def log(self, message: str):
        """Adds a message to the log widget with a timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()

    def save_log(self):
        """Saves the current log to a text file."""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Log", "upscaler_log.txt", "Text Files (*.txt)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.log(f"Log saved to: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log: {str(e)}")

    def show_about(self):
        """Shows the 'About' dialog."""
        QMessageBox.about(
            self, "About Anime-Media-Upscaler",
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
        """Loads application settings from QSettings."""
        output_folder = self.settings.value('output_folder', '')
        if output_folder and os.path.exists(output_folder):
            self.output_folder = output_folder
            self.output_path_label.setText(output_folder)
            self.output_path_label.setStyleSheet("color: white;")
        else:
            self.output_folder = None
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """Saves settings and stops processing on application close."""
        self.settings.setValue('geometry', self.saveGeometry())
        if self.stop_btn.isEnabled():
            self.stop_processing()
        event.accept()
