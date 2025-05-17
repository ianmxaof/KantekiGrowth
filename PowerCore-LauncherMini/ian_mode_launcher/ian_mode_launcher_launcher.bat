@echo off
color 0F
:menu
echo ===============================
echo   Ian Mode Launcher - Selector
echo ===============================
echo.
echo 1. Run GUI (ian_mode_launcher_gui.py)
echo 2. Run Main Executable (ian_mode_launcher.exe)
echo 3. Clean Logs
echo 4. Clean Prompts
echo 5. Exit
echo.
set /p choice=Choose an option (1-5): 
if "%choice%"=="1" goto gui
if "%choice%"=="2" goto exe
if "%choice%"=="3" goto cleanlogs
if "%choice%"=="4" goto cleanprompts
if "%choice%"=="5" exit

echo Invalid choice. Try again.
goto menu

:gui
python ian_mode_launcher_gui.py
exit

:exe
dist\ian_mode_launcher.exe
exit

:cleanlogs
python -c "import ian_mode_launcher; ian_mode_launcher.clean_invalid_logs()"
echo Logs cleaned.
pause
goto menu

:cleanprompts
python -c "print('Prompt cleaning stub: implement as needed.')"
echo Prompts cleaned (stub).
pause
goto menu 