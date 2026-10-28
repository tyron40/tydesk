@echo off
cd /d "%~dp0"
if exist "System Calculator.exe" (start "" "%~dp0System Calculator.exe" /restore) else (echo Run Start-System-Calculator.cmd first. & pause)
