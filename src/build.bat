@echo off
echo Building Anime Media Upscaler...
pyinstaller --name "AMU" ^
  --onefile ^
  --windowed ^
  --icon=favicon.ico ^
  --add-data "bin;bin" ^
  --add-data "models;models" ^
  --add-data "favicon.ico;." ^
  main.py
pause
