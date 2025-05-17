@echo off
setlocal

REM === CONFIG ===
set ICON_PATH=E:\projects\icon_placeholders\favicon.ico
set MAIN_SCRIPT=ian_mode_launcher.py
set EXE_NAME=ian_mode_launcher.exe
set DIST_DIR=dist
set LOG_FILE=build.log
set REQUIREMENTS=requirements.txt
set SPEC_FILE=pyinstaller.spec
set CONFIG_FILE=ian_mode.json
set ERROR_LOG=startup_error.log

REM === LOGGING ===
echo [BUILD] Starting build at %DATE% %TIME% > %LOG_FILE%

REM === INSTALL DEPENDENCIES ===
echo [BUILD] Installing Python dependencies... >> %LOG_FILE%
pip install -r %REQUIREMENTS% >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies. See %LOG_FILE%.
    exit /b 1
)

REM === CHECK PYINSTALLER ===
echo [BUILD] Checking for PyInstaller... >> %LOG_FILE%
pip show pyinstaller >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [BUILD] PyInstaller not found. Installing... >> %LOG_FILE%
    pip install pyinstaller >> %LOG_FILE% 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install PyInstaller. See %LOG_FILE%.
        exit /b 1
    )
)

REM === BUILD EXE ===
echo [BUILD] Building .exe with PyInstaller... >> %LOG_FILE%
pyinstaller --onefile --icon="%ICON_PATH%" %MAIN_SCRIPT% >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed. See %LOG_FILE%.
    exit /b 1
)

REM === BUNDLE CONFIG FILE ===
echo [BUILD] Copying config file to dist... >> %LOG_FILE%
copy /Y %CONFIG_FILE% %DIST_DIR%\%CONFIG_FILE% >> %LOG_FILE% 2>&1

REM === POST-BUILD TEST ===
echo [BUILD] Testing built .exe... >> %LOG_FILE%
if exist %DIST_DIR%\ian_mode_launcher.exe (
    %DIST_DIR%\ian_mode_launcher.exe --help >> %LOG_FILE% 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] .exe failed to run. See %LOG_FILE%.
        if exist %DIST_DIR%\%ERROR_LOG% (
            echo [ERROR] startup_error.log contents: >> %LOG_FILE%
            type %DIST_DIR%\%ERROR_LOG% >> %LOG_FILE%
        )
        exit /b 1
    )
    echo [BUILD] .exe built and ran successfully. >> %LOG_FILE%
    echo [SUCCESS] Build complete. .exe is in %DIST_DIR%\ian_mode_launcher.exe
) else (
    echo [ERROR] .exe not found in %DIST_DIR%. See %LOG_FILE%.
    exit /b 1
)

REM === OPTIONAL: NSIS INSTALLER STUB ===
echo [INFO] To create an installer, add your NSIS script and call makensis here. >> %LOG_FILE%
REM Example: makensis my_installer.nsi >> %LOG_FILE% 2>&1

endlocal 