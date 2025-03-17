import sys
import os
import subprocess
import cv2
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QProgressBar,
    QComboBox,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtGui import QIcon, QMovie
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot

# Determine the absolute path of the current script and project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
bin_dir = os.path.join(project_root, "bin")
resources_dir = os.path.join(project_root, "resources")


class UpscaleWorker(QThread):
    progress = pyqtSignal(int)
    completed = pyqtSignal()
    error = pyqtSignal(str)
    file_progress = pyqtSignal(str)

    def __init__(self, files, output_dir, resolution, interpolation):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.resolution = resolution
        self.interpolation = interpolation
        # Reference ffmpeg.exe from the bin folder
        self.ffmpeg_path = os.path.join(bin_dir, "ffmpeg.exe")

    def run(self):
        video_ext = [".mp4", ".avi", ".mov", ".mkv"]
        image_ext = [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]
        total_frames = 0

        # Calculate total frames for progress
        for file in self.files:
            ext = os.path.splitext(file)[1].lower()
            if ext in video_ext:
                cap = cv2.VideoCapture(file)
                if cap.isOpened():
                    total_frames += int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    cap.release()
            elif ext in image_ext:
                total_frames += 1

        processed = 0
        for file_path in self.files:
            self.file_progress.emit(os.path.basename(file_path))
            try:
                ext = os.path.splitext(file_path)[1].lower()
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_path = os.path.join(
                    self.output_dir, f"{base_name}_upscaled{ext}"
                )

                # Process video files
                if ext in video_ext:
                    cap = cv2.VideoCapture(file_path)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                    # Calculate target resolution
                    if self.resolution == "1080p":
                        target_height = 1080
                        scale = target_height / height
                        target_width = int(width * scale)
                    else:
                        target_width = 2048 if self.resolution == "2K" else 3840
                        scale = target_width / width
                        target_height = int(height * scale)

                    # Video writer setup
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    temp_video = os.path.join(self.output_dir, f"temp_{base_name}.mp4")
                    out = cv2.VideoWriter(
                        temp_video, fourcc, fps, (target_width, target_height)
                    )

                    interp = {
                        "Nearest": cv2.INTER_NEAREST,
                        "Linear": cv2.INTER_LINEAR,
                        "Cubic": cv2.INTER_CUBIC,
                        "Lanczos": cv2.INTER_LANCZOS4,
                    }[self.interpolation]

                    for _ in range(frame_count):
                        ret, frame = cap.read()
                        if not ret:
                            break
                        resized = cv2.resize(
                            frame, (target_width, target_height), interpolation=interp
                        )
                        out.write(resized)
                        processed += 1
                        self.progress.emit(int((processed / total_frames) * 100))

                    cap.release()
                    out.release()

                    # Audio processing
                    audio_temp = os.path.join(self.output_dir, "temp_audio.aac")
                    try:
                        subprocess.run(
                            [
                                self.ffmpeg_path,
                                "-i",
                                file_path,
                                "-vn",
                                "-acodec",
                                "copy",
                                audio_temp,
                            ],
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                    except subprocess.CalledProcessError:
                        audio_exists = False
                    else:
                        audio_exists = (
                            os.path.exists(audio_temp)
                            and os.path.getsize(audio_temp) > 0
                        )

                    if audio_exists:
                        subprocess.run(
                            [
                                self.ffmpeg_path,
                                "-i",
                                temp_video,
                                "-i",
                                audio_temp,
                                "-c:v",
                                "copy",
                                "-c:a",
                                "aac",
                                "-strict",
                                "experimental",
                                output_path,
                            ],
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        os.remove(audio_temp)
                    else:
                        os.rename(temp_video, output_path)

                    if os.path.exists(temp_video):
                        os.remove(temp_video)

                # Process image files
                elif ext in image_ext:
                    img = cv2.imread(file_path)
                    if img is None:
                        raise ValueError(f"Invalid image file: {file_path}")
                    height, width = img.shape[:2]

                    if self.resolution == "1080p":
                        target_height = 1080
                        scale = target_height / height
                        target_width = int(width * scale)
                    else:
                        target_width = 2048 if self.resolution == "2K" else 3840
                        scale = target_width / width
                        target_height = int(height * scale)

                    interp = {
                        "Nearest": cv2.INTER_NEAREST,
                        "Linear": cv2.INTER_LINEAR,
                        "Cubic": cv2.INTER_CUBIC,
                        "Lanczos": cv2.INTER_LANCZOS4,
                    }[self.interpolation]

                    resized = cv2.resize(
                        img, (target_width, target_height), interpolation=interp
                    )
                    cv2.imwrite(output_path, resized)
                    processed += 1
                    self.progress.emit(int((processed / total_frames) * 100))

            except Exception as e:
                self.error.emit(f"Error processing {file_path}: {str(e)}")
                return

        self.completed.emit()


class MediaUpscaler(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SSUpscaler")
        # Use the logo from the resources folder
        logo_path = os.path.join(resources_dir, "logo.png")
        self.setWindowIcon(QIcon(logo_path))
        self.setGeometry(100, 100, 900, 650)
        self.save_folder = ""

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("SSUpscaler")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(header)

        # File list section
        file_list_label = QLabel("Selected Files:")
        file_list_label.setStyleSheet("font-size: 16px;")
        self.layout.addWidget(file_list_label)
        self.file_list = QListWidget()
        self.file_list.setFixedHeight(150)
        self.layout.addWidget(self.file_list)

        # File controls (Add, Remove, Clear)
        file_controls = QHBoxLayout()
        self.add_btn = QPushButton("Add Files")
        self.remove_btn = QPushButton("Remove Selected")
        self.clear_btn = QPushButton("Clear All")
        self.add_btn.clicked.connect(self.add_files)
        self.remove_btn.clicked.connect(self.remove_files)
        self.clear_btn.clicked.connect(self.file_list.clear)
        file_controls.addWidget(self.add_btn)
        file_controls.addWidget(self.remove_btn)
        file_controls.addWidget(self.clear_btn)
        self.layout.addLayout(file_controls)

        # Output directory section
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Directory:")
        output_label.setStyleSheet("font-size: 16px;")
        self.output_entry = QLineEdit()
        self.output_btn = QPushButton("Select Output Folder")
        # Use folder icon from the resources folder
        folder_icon_path = os.path.join(resources_dir, "folder.png")
        self.output_btn.setIcon(QIcon(folder_icon_path))
        self.output_btn.clicked.connect(self.select_output)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_entry)
        output_layout.addWidget(self.output_btn)
        self.layout.addLayout(output_layout)

        # Settings: Resolution and Interpolation
        settings_layout = QHBoxLayout()
        res_label = QLabel("Resolution:")
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1080p", "2K", "4K"])
        self.resolution_combo.setCurrentIndex(0)
        interp_label = QLabel("Interpolation:")
        self.interp_combo = QComboBox()
        self.interp_combo.addItems(["Nearest", "Linear", "Cubic", "Lanczos"])
        self.interp_combo.setCurrentIndex(2)
        settings_layout.addWidget(res_label)
        settings_layout.addWidget(self.resolution_combo)
        settings_layout.addSpacing(20)
        settings_layout.addWidget(interp_label)
        settings_layout.addWidget(self.interp_combo)
        self.layout.addLayout(settings_layout)

        # Start processing button
        self.start_btn = QPushButton("Start Batch Processing")
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self.start_processing)
        self.layout.addWidget(self.start_btn)

        # Status and progress section
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.layout.addWidget(self.progress_bar)
        self.loader = QLabel()
        self.loader.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use loader gif from the resources folder
        loader_gif_path = os.path.join(resources_dir, "loader.gif")
        self.loader_movie = QMovie(loader_gif_path)
        self.loader.setMovie(self.loader_movie)
        self.loader.setVisible(False)
        self.layout.addWidget(self.loader)

        # Apply a professional dark style using a global stylesheet
        self.setStyleSheet(
            """
            QMainWindow { background-color: #343a40; }
            QWidget { background-color: #343a40; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8f9fa; }
            QLineEdit {
                background-color: #495057;
                color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                background-color: #007bff;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #0069d9; }
            QListWidget {
                background-color: #495057;
                color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
            QProgressBar {
                background-color: #495057;
                color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 4px;
            }
        """
        )

        # Initialize worker placeholder
        self.worker = None

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media Files",
            "",
            "All Media (*.mp4 *.avi *.mov *.mkv *.png *.jpg *.jpeg *.bmp *.tiff);;"
            "Video Files (*.mp4 *.avi *.mov *.mkv);;"
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)",
        )
        for file in files:
            QListWidgetItem(file, self.file_list)

    def remove_files(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def select_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_entry.setText(directory)

    def start_processing(self):
        if not self.validate_inputs():
            return

        self.start_btn.setEnabled(False)
        self.loader.setVisible(True)
        self.loader_movie.start()
        self.progress_bar.setValue(0)

        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        output_dir = self.output_entry.text().strip()
        resolution = self.resolution_combo.currentText()
        interpolation = self.interp_combo.currentText()

        self.worker = UpscaleWorker(files, output_dir, resolution, interpolation)
        self.worker.progress.connect(self.update_progress)
        self.worker.completed.connect(self.processing_complete)
        self.worker.error.connect(self.show_error)
        self.worker.file_progress.connect(self.update_file_status)
        self.worker.start()

    def validate_inputs(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Error", "Please add media files to process!")
            return False
        if not os.path.exists(self.output_entry.text().strip()):
            QMessageBox.warning(
                self, "Error", "Please select a valid output directory!"
            )
            return False
        return True

    @pyqtSlot(int)
    def update_progress(self, value):
        self.progress_bar.setValue(value)

    @pyqtSlot()
    def processing_complete(self):
        self.loader_movie.stop()
        self.loader.setVisible(False)
        self.start_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        QMessageBox.information(
            self,
            "Success",
            f"Batch processing completed!\nFiles saved to:\n{self.output_entry.text()}",
        )

    @pyqtSlot(str)
    def show_error(self, message):
        self.loader_movie.stop()
        self.loader.setVisible(False)
        self.start_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", message)

    @pyqtSlot(str)
    def update_file_status(self, filename):
        self.status_label.setText(f"Processing: {filename}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MediaUpscaler()
    window.show()
    sys.exit(app.exec())
