"""
Project: sharpify-gui
Author: ukr
Version: 1.0.0
License: MIT
Repository: https://github.com/uikraft-hub/sharpify-gui
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
    app.setApplicationName("sharpify-gui")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("UKR-PROJECTS")

    icon_path = "favicon.ico"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = AnimeUpscalerGUI()
    window.show()

    window.log("sharpify-gui v2.0.0 started")
    window.log("Checking dependencies...")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
