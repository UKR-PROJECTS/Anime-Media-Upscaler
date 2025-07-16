"""
This module defines the `UpscaleWorker` class, which is responsible for handling
the upscaling process in a separate thread to avoid blocking the main UI.

The `UpscaleWorker` class is a `QRunnable` that can be executed in a `QThreadPool`.
It handles both image and video upscaling by:
- Finding the Real-ESRGAN executable and models.
- Constructing and running the appropriate command-line commands.
- For videos, it extracts frames, upscales them individually, and then reassembles the video.
- Emitting signals to update the UI with progress, logs, and results.
"""

import os
import subprocess
import shutil
import tempfile
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable


class WorkerSignals(QObject):
    """Defines signals available from a running worker thread."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)


class UpscaleWorker(QRunnable):
    """
    A worker thread for upscaling images and videos.
    Inherits from QRunnable to allow for execution in a QThreadPool.
    """

    def __init__(self, file_path: str, output_path: str, settings: Dict[str, Any]):
        """
        Initializes the worker.

        Args:
            file_path: The path to the input file.
            output_path: The path to the output file.
            settings: A dictionary of upscaling settings.
        """
        super().__init__()
        self.file_path = file_path
        self.output_path = output_path
        self.settings = settings
        self.signals = WorkerSignals()
        self.is_cancelled = False
        self.current_process = None

    def run(self):
        """The main entry point for the worker thread."""
        try:
            # Determine whether to upscale an image or a video based on the file extension
            if self.file_path.lower().endswith(
                (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv")
            ):
                self._upscale_video()
            else:
                self._upscale_image()
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

    def _upscale_image(self):
        """Upscales a single image using Real-ESRGAN."""
        try:
            # Find the Real-ESRGAN executable
            realesrgan_path = self._find_realesrgan_executable()
            if not realesrgan_path:
                raise FileNotFoundError(
                    "Real-ESRGAN executable not found. Please install Real-ESRGAN."
                )

            # Find the models directory
            models_dir = self._find_models_directory(realesrgan_path)
            if not models_dir:
                raise FileNotFoundError(
                    "Real-ESRGAN models directory not found. Please ensure models are installed."
                )

            # Get the selected model and check if it exists
            model_name = self.settings.get("model", "realesr-animevideov3-x4")
            model_file = os.path.join(models_dir, f"{model_name}.param")

            if not os.path.exists(model_file):
                available_models = self._get_available_models(models_dir)
                if available_models:
                    requested_model = self.settings.get(
                        "model", "realesr-animevideov3-x4"
                    )
                    if requested_model in available_models:
                        model_name = requested_model
                    else:
                        model_name = available_models[0]
                    self.signals.log.emit(
                        f"Model '{self.settings.get('model')}' not found, using '{model_name}' instead"
                    )
                else:
                    raise FileNotFoundError(
                        f"No Real-ESRGAN models found in {models_dir}"
                    )

            # Construct the command to run Real-ESRGAN
            cmd = [
                realesrgan_path,
                "-i",
                self.file_path,
                "-o",
                self.output_path,
                "-n",
                model_name,
                "-f",
                self.settings.get("format", "jpg"),
            ]

            if self.settings.get("use_gpu", True):
                cmd.extend(["-g", "0"])

            if self.settings.get("tile_size"):
                cmd.extend(["-t", str(self.settings["tile_size"])])

            self.signals.log.emit(f"Processing: {os.path.basename(self.file_path)}")
            self.signals.log.emit(f"Command: {' '.join(cmd)}")

            # Start the Real-ESRGAN process
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            stdout, stderr = self.current_process.communicate()
            process = self.current_process

            if process.returncode != 0:
                raise RuntimeError(f"Upscaling failed: {stderr}")

            self.signals.log.emit(f"✓ Completed: {os.path.basename(self.output_path)}")
            self.signals.result.emit(self.output_path)

        except Exception as e:
            self.signals.error.emit(f"Image upscaling error: {str(e)}")

    def _find_models_directory(self, realesrgan_path: str) -> Optional[str]:
        """Finds the Real-ESRGAN models directory."""
        exe_dir = os.path.dirname(realesrgan_path)
        possible_dirs = [
            os.path.join(exe_dir, "models"),
            os.path.join(exe_dir, "..", "models"),
            os.path.join(os.getcwd(), "models"),
            os.path.join(os.getcwd(), "bin", "models"),
        ]
        for models_dir in possible_dirs:
            if os.path.exists(models_dir) and os.path.isdir(models_dir):
                return models_dir
        return None

    def _get_available_models(self, models_dir: str) -> List[str]:
        """Gets a list of available Real-ESRGAN models."""
        if not os.path.exists(models_dir):
            return []
        models = []
        for file in os.listdir(models_dir):
            if file.endswith(".param"):
                model_name = file.replace(".param", "")
                bin_file = os.path.join(models_dir, f"{model_name}.bin")
                if os.path.exists(bin_file):
                    models.append(model_name)
        return models

    def _upscale_video(self):
        """Upscales a video by extracting frames, upscaling them, and reassembling the video."""
        try:
            # Create temporary directories for frames and upscaled frames
            temp_dir = tempfile.mkdtemp(prefix="anime_upscaler_")
            frames_dir = os.path.join(temp_dir, "frames")
            upscaled_dir = os.path.join(temp_dir, "upscaled")
            os.makedirs(frames_dir, exist_ok=True)
            os.makedirs(upscaled_dir, exist_ok=True)

            try:
                # Extract frames from the video
                self.signals.log.emit("Extracting video frames...")
                self._extract_frames(self.file_path, frames_dir)
                if self.is_cancelled:
                    return

                # Upscale the extracted frames
                self.signals.log.emit("Upscaling frames...")
                self._upscale_frames(frames_dir, upscaled_dir)
                if self.is_cancelled:
                    return

                # Reassemble the video from the upscaled frames
                self.signals.log.emit("Reassembling video...")
                self._reassemble_video(upscaled_dir, self.output_path, self.file_path)

                self.signals.log.emit(
                    f"✓ Video upscaling completed: {os.path.basename(self.output_path)}"
                )
                self.signals.result.emit(self.output_path)
            finally:
                # Clean up the temporary directories
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.signals.log.emit(
                        f"Warning: Could not clean up temporary files: {str(e)}"
                    )
        except Exception as e:
            self.signals.error.emit(f"Video upscaling error: {str(e)}")

    def _extract_frames(self, video_path: str, frames_dir: str):
        """Extracts frames from a video using FFmpeg."""
        ffmpeg_path = self._get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            "-i",
            video_path,
            "-q:v",
            "1",
            "-pix_fmt",
            "rgb24",
            os.path.join(frames_dir, "frame_%06d.png"),
        ]
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if process.returncode != 0:
            raise RuntimeError(f"Frame extraction failed: {process.stderr}")

    def _upscale_frames(self, frames_dir: str, upscaled_dir: str):
        """Upscales a directory of frames using Real-ESRGAN."""
        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".png")])
        if not frame_files:
            raise RuntimeError("No frames were extracted from the video")

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
                "-i",
                input_path,
                "-o",
                output_path,
                "-n",
                self.settings.get("model", "realesr-animevideov3-x4"),
            ]
            if self.settings.get("use_gpu", True):
                cmd.extend(["-g", "0"])
            if self.settings.get("tile_size"):
                cmd.extend(["-t", str(self.settings["tile_size"])])
            process = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if process.returncode != 0:
                self.signals.log.emit(f"Warning: Frame {frame_file} failed to upscale")
            progress = int((i + 1) / total_frames * 100)
            self.signals.progress.emit(progress)

    def _reassemble_video(
        self, upscaled_dir: str, output_path: str, original_video: str
    ):
        """Reassembles a video from a directory of frames using FFmpeg."""
        ffmpeg_path = self._get_ffmpeg_path()
        temp_audio = os.path.join(os.path.dirname(output_path), "temp_audio.aac")
        audio_cmd = [
            ffmpeg_path,
            "-i",
            original_video,
            "-vn",
            "-acodec",
            "copy",
            temp_audio,
        ]
        subprocess.run(
            audio_cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        reassemble_cmd = [
            ffmpeg_path,
            "-framerate",
            str(self.settings.get("fps", 24)),
            "-i",
            os.path.join(upscaled_dir, "frame_%06d.png"),
            "-i",
            temp_audio,
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            str(self.settings.get("quality", 18)),
            output_path,
        ]
        process = subprocess.run(
            reassemble_cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            os.remove(temp_audio)
        except:
            pass
        if process.returncode != 0:
            raise RuntimeError(f"Video reassembly failed: {process.stderr}")

    def _find_realesrgan_executable(self) -> Optional[str]:
        """Finds the Real-ESRGAN executable."""
        possible_names = [
            "realesrgan-ncnn-vulkan",
            "realesrgan-ncnn-vulkan.exe",
            "realsr-esrgan",
            "realsr-esrgan.exe",
        ]
        search_paths = [".", "bin", os.path.join(os.getcwd(), "bin")]
        for path in search_paths:
            for name in possible_names:
                full_path = os.path.join(path, name)
                if os.path.isfile(full_path):
                    return full_path
        for name in possible_names:
            if shutil.which(name):
                return shutil.which(name)
        return None

    def _get_ffmpeg_path(self) -> str:
        """Gets the path to the FFmpeg executable."""
        bin_ffmpeg = os.path.join("bin", "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.isfile(bin_ffmpeg):
            return bin_ffmpeg
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        raise FileNotFoundError(
            "FFmpeg not found. Please ensure ffmpeg is in the bin folder or in PATH."
        )

    def cancel(self):
        """Cancels the current upscaling process."""
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
