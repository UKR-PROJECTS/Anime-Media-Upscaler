@echo off
echo Building Anime Media Upscaler...
pyinstaller --name "sharpify-gui" ^
  --windowed ^
  --icon=favicon.ico ^
  main.py
pause
