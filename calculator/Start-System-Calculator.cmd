@echo off
setlocal
cd /d "%~dp0"
set "compiler=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%compiler%" set "compiler=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%compiler%" (
 echo Windows .NET Framework 4.x is required.
 pause
 exit /b 1
)
if not exist "System Calculator.exe" (
 "%compiler%" /nologo /target:winexe /out:"System Calculator.exe" /win32icon:calculator.ico /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Security.dll Calculator.cs Dashboard.cs HiddenFiles.cs
 if errorlevel 1 (
  echo Build failed. Keep all extracted files together in a writable folder.
  pause
  exit /b 1
 )
)
start "" "%~dp0System Calculator.exe"
