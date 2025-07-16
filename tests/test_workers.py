import unittest
import os
import sys
from unittest.mock import patch, MagicMock, call

# Add the src directory to the Python path to allow for 'from app...' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(project_root, "src"))

from app.workers import UpscaleWorker


class TestUpscaleWorker(unittest.TestCase):
    """Tests for the UpscaleWorker class."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_signals = MagicMock()
        self.settings = {
            "model": "realesrgan-x4plus",
            "format": "png",
            "use_gpu": True,
            "tile_size": 0,
            "fps": 30,
            "quality": 23,
        }
        # We instantiate the worker but will call run() inside patched contexts
        self.worker = UpscaleWorker(
            file_path="dummy/input.jpg",
            output_path="dummy/output.png",
            settings=self.settings,
        )
        self.worker.signals = self.mock_signals

    @patch("app.workers.subprocess.Popen")
    @patch(
        "app.workers.UpscaleWorker._find_realesrgan_executable",
        return_value="path/to/realesrgan",
    )
    @patch(
        "app.workers.UpscaleWorker._find_models_directory",
        return_value="path/to/models",
    )
    @patch("os.path.exists", return_value=True)
    def test_upscale_image_success(
        self, mock_exists, mock_find_models, mock_find_exe, mock_popen
    ):
        """Test the successful upscaling of an image."""
        # Arrange
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        self.worker.file_path = "dummy/input.jpg"

        # Act
        self.worker.run()

        # Assert
        mock_popen.assert_called_once()
        self.mock_signals.log.emit.assert_any_call("✓ Completed: output.png")
        self.mock_signals.result.emit.assert_called_once_with("dummy/output.png")
        self.mock_signals.error.emit.assert_not_called()
        self.mock_signals.finished.emit.assert_called_once()

    @patch("app.workers.UpscaleWorker._find_realesrgan_executable", return_value=None)
    def test_upscale_image_realesrgan_not_found(self, mock_find_exe):
        """Test image upscaling failure when Real-ESRGAN executable is not found."""
        # Arrange
        self.worker.file_path = "dummy/input.jpg"

        # Act
        self.worker.run()

        # Assert
        self.mock_signals.error.emit.assert_called_once_with(
            "Image upscaling error: Real-ESRGAN executable not found. Please install Real-ESRGAN."
        )
        self.mock_signals.finished.emit.assert_called_once()

    @patch("app.workers.subprocess.run")
    @patch(
        "app.workers.UpscaleWorker._find_realesrgan_executable",
        return_value="path/to/realesrgan",
    )
    @patch("app.workers.UpscaleWorker._get_ffmpeg_path", return_value="path/to/ffmpeg")
    @patch("tempfile.mkdtemp", return_value="dummy/temp")
    @patch("os.makedirs")
    @patch("os.listdir", return_value=["frame_000001.png"])
    @patch("shutil.rmtree")
    def test_upscale_video_success(
        self,
        mock_rmtree,
        mock_listdir,
        mock_makedirs,
        mock_mkdtemp,
        mock_ffmpeg_path,
        mock_find_exe,
        mock_sub_run,
    ):
        """Test the successful upscaling of a video."""
        # Arrange
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr = ""
        mock_sub_run.return_value = mock_process
        self.worker.file_path = "dummy/input.mp4"

        # Act
        self.worker.run()

        # Assert
        self.assertEqual(
            mock_sub_run.call_count, 4
        )  # extract, upscale, audio, reassemble
        self.mock_signals.log.emit.assert_any_call(
            "✓ Video upscaling completed: output.png"
        )
        self.mock_signals.result.emit.assert_called_once_with("dummy/output.png")
        self.mock_signals.error.emit.assert_not_called()
        self.mock_signals.finished.emit.assert_called_once()
        mock_rmtree.assert_called_once_with("dummy/temp")

    @patch(
        "app.workers.UpscaleWorker._get_ffmpeg_path",
        side_effect=FileNotFoundError("FFmpeg not found"),
    )
    def test_upscale_video_ffmpeg_not_found(self, mock_ffmpeg_path):
        """Test video upscaling failure when FFmpeg is not found."""
        # Arrange
        self.worker.file_path = "dummy/input.mp4"

        # Act
        self.worker.run()

        # Assert
        self.mock_signals.error.emit.assert_called_once_with(
            "Video upscaling error: FFmpeg not found"
        )
        self.mock_signals.finished.emit.assert_called_once()

    def test_cancel_process(self):
        """Test the cancellation of the upscaling process."""
        # Arrange
        mock_process = MagicMock()
        self.worker.current_process = mock_process
        self.worker.is_cancelled = False

        # Act
        self.worker.cancel()

        # Assert
        self.assertTrue(self.worker.is_cancelled)
        mock_process.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
