"""
This module defines the `SettingsDialog` class, which provides a dialog window
for configuring advanced upscaling settings.

The dialog allows users to adjust settings such as:
- The AI model to use for upscaling.
- Performance settings, including GPU acceleration and tile size.
- Video processing settings, such as output FPS and quality.
- The output format for upscaled images.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
    QCheckBox, QSpinBox, QDialogButtonBox
)
from typing import Dict, Any

class SettingsDialog(QDialog):
    """A dialog for configuring advanced upscaling settings."""

    def __init__(self, parent=None):
        """Initializes the settings dialog and its UI components."""
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.setModal(True)
        self.resize(400, 500)

        layout = QVBoxLayout(self)

        # AI Model Settings
        model_group = QGroupBox("AI Model Settings")
        model_layout = QFormLayout(model_group)
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'realesr-animevideov3-x2', 'realesr-animevideov3-x3',
            'realesr-animevideov3-x4', 'realesrgan-x4plus',
            'realesrgan-x4plus-anime'
        ])
        model_layout.addRow("Model:", self.model_combo)

        # Performance Settings
        perf_group = QGroupBox("Performance Settings")
        perf_layout = QFormLayout(perf_group)
        self.gpu_check = QCheckBox("Use GPU Acceleration")
        self.gpu_check.setChecked(True)
        self.gpu_check.setToolTip("Enable GPU processing for faster upscaling (requires compatible graphics card)")
        perf_layout.addRow(self.gpu_check)
        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(0, 2048)
        self.tile_spin.setValue(400)
        self.tile_spin.setSpecialValueText("Auto")
        self.tile_spin.setToolTip(
            "Controls GPU memory usage:\n"
            "• Lower values (100-200): Less GPU memory, slower processing\n"
            "• Higher values (600-1000): More GPU memory, faster processing\n"
            "• Auto: Let Real-ESRGAN decide based on available memory"
        )
        perf_layout.addRow("Tile Size (GPU Memory):", self.tile_spin)

        # Video Processing Settings
        video_group = QGroupBox("Video Processing Settings")
        video_layout = QFormLayout(video_group)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(24)
        self.fps_spin.setToolTip("Output video framerate (frames per second)")
        video_layout.addRow("Output FPS:", self.fps_spin)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(0, 51)
        self.quality_spin.setValue(18)
        self.quality_spin.setToolTip(
            "Video quality setting (CRF):\n"
            "• 0-17: Visually lossless (very large files)\n"
            "• 18-23: High quality (recommended)\n"
            "• 24-28: Medium quality\n"
            "• 29+: Lower quality (smaller files)"
        )
        video_layout.addRow("Video Quality (CRF):", self.quality_spin)

        # Output Format Settings
        output_group = QGroupBox("Output Format Settings")
        output_layout = QFormLayout(output_group)
        self.format_combo = QComboBox()
        self.format_combo.addItems(['jpg', 'png', 'webp'])
        self.format_combo.setToolTip(
            "Output format for images:\n"
            "• JPG: Smaller files, good for photos\n"
            "• PNG: Lossless, larger files, supports transparency\n"
            "• WebP: Modern format, good compression"
        )
        output_layout.addRow("Image Format:", self.format_combo)

        layout.addWidget(model_group)
        layout.addWidget(perf_group)
        layout.addWidget(video_group)
        layout.addWidget(output_group)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self) -> Dict[str, Any]:
        """Returns the current settings from the dialog's UI components."""
        return {
            'model': self.model_combo.currentText(),
            'use_gpu': self.gpu_check.isChecked(),
            'tile_size': self.tile_spin.value() if self.tile_spin.value() > 0 else None,
            'fps': self.fps_spin.value(),
            'quality': self.quality_spin.value(),
            'format': self.format_combo.currentText()
        }

    def set_settings(self, settings: Dict[str, Any]):
        """Sets the dialog's UI components based on the provided settings."""
        self.model_combo.setCurrentText(settings.get('model', 'realesr-animevideov3-x2'))
        self.gpu_check.setChecked(settings.get('use_gpu', True))
        self.tile_spin.setValue(settings.get('tile_size', 400) or 0)
        self.fps_spin.setValue(settings.get('fps', 24))
        self.quality_spin.setValue(settings.get('quality', 18))
        self.format_combo.setCurrentText(settings.get('format', 'jpg'))
