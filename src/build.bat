@echo off
echo Building Anime Media Upscaler...
pyinstaller --name "AMU" ^
  --windowed ^
  --icon=favicon.ico ^
  main.py
pause
