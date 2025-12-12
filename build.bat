@echo off
echo ================================
echo Checking Python...
echo ================================
python --version
if errorlevel 1 (
    echo Python not found. Please install Python first.
    pause
    exit /b 1
)

echo ================================
echo Installing venv (if needed)...
echo ================================
python -m pip install --upgrade pip
python -m pip install virtualenv

echo ================================
echo Creating virtual environment...
echo ================================
python -m venv venv

echo ================================
echo Activating virtual environment...
echo ================================
call venv\Scripts\activate.bat

echo ================================
echo Installing requirements...
echo ================================
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo requirements.txt not found, skipping.
)

echo ================================
echo Installing PyInstaller...
echo ================================
pip install pyinstaller

echo ================================
echo Building main.py with PyInstaller...
echo ================================
pyinstaller --onefile --noconsole --collect-all sounddevice ftx1gui.py

echo ================================
echo Build finished.
echo Output is in the dist folder.
echo ================================
pause
