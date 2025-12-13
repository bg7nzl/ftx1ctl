@echo off
chcp 65001 >nul
setlocal

echo ================================
echo 1. 正在检查 Python 3.12 环境...
echo ================================

:: 尝试通过 Windows 官方启动器调用 Python 3.12
set PYTHON_CMD=py -3.12

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python 3.12！
    echo.
    pause
    exit /b 1
)

echo 检测到 Python 3.12，正在创建专用打包环境...
REM if exist venv rmdir /s /q venv

:: 使用 3.12 创建虚拟环境
%PYTHON_CMD% -m venv venv

echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo ================================
echo 2. 正在安装依赖库...
echo ================================

:: 1) 先安装 Nuitka 和构建工具 (zstandard 用于单文件压缩)
pip install nuitka zstandard

:: 2) 再安装你的项目依赖 (requirements.txt)
if exist requirements.txt (
    echo 正在从 requirements.txt 安装库...
    pip install -r requirements.txt
) else (
    echo [警告] 没找到 requirements.txt，尝试手动安装常用库...
    pip install sounddevice numpy matplotlib scipy pyserial
)

echo ================================
echo 3. 开始使用 Nuitka 打包...
echo ================================
:: Python 3.12 + Nuitka + MinGW64 (自动下载) = 稳定打包
:: 增加了 --enable-plugin=tk-inter 和 numpy 支持
python -m nuitka --mingw64 --lto=no --onefile --windows-console-mode=disable --enable-plugin=tk-inter --enable-plugin=numpy --include-package=sounddevice --remove-output ftx1gui.py

echo ================================
echo 打包完成！文件名为 ftx1gui.exe
echo ================================
pause