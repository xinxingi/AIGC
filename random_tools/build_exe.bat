@echo off
setlocal

REM 进入脚本所在目录（random_tools）
cd /d %~dp0

REM 清理旧构建
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM 安装依赖（可选：若已安装可跳过）
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM 使用 PyInstaller 打包
pyinstaller ^
  --noconfirm ^
  --clean ^
  --name "LuckyDraw" ^
  --windowed ^
  --add-data "participants.json;." ^
  gui_enhanced.py

if %errorlevel% neq 0 (
  echo Build failed.
  exit /b %errorlevel%
)

echo Build succeeded. Output in dist\LuckyDraw\
endlocal

