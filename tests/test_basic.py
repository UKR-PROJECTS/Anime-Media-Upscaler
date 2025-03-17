import os
import unittest
import sys

# Add the src folder to the path so we can import main.py
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from main import MediaUpscaler, resources_dir, bin_dir  # Import from main.py

from PyQt6.QtWidgets import QApplication

# Create a single QApplication instance for the tests
app = QApplication(sys.argv)

class TestBasic(unittest.TestCase):
    def test_resources_exist(self):
        """Test that essential resource files exist."""
        logo_path = os.path.join(resources_dir, "logo.png")
        folder_icon_path = os.path.join(resources_dir, "folder.png")
        loader_gif_path = os.path.join(resources_dir, "loader.gif")
        self.assertTrue(os.path.exists(logo_path), f"Logo not found at {logo_path}")
        self.assertTrue(os.path.exists(folder_icon_path), f"Folder icon not found at {folder_icon_path}")
        self.assertTrue(os.path.exists(loader_gif_path), f"Loader GIF not found at {loader_gif_path}")

    def test_ffmpeg_exists(self):
        """Test that ffmpeg.exe exists in the bin folder."""
        ffmpeg_path = os.path.join(bin_dir, "ffmpeg.exe")
        self.assertTrue(os.path.exists(ffmpeg_path), f"ffmpeg.exe not found at {ffmpeg_path}")

    def test_main_window_instantiation(self):
        """Test that the MediaUpscaler window can be instantiated."""
        window = MediaUpscaler()
        self.assertIsNotNone(window)
        # Optionally, check if window title is set correctly
        self.assertEqual(window.windowTitle(), "SSUpscaler")


if __name__ == '__main__':
    unittest.main()
