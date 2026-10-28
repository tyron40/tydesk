# System Calculator 1.4

Open System Calculator.exe on 64-bit Windows 10/11. The published single EXE
includes its .NET runtime; no separate .NET installation is needed.
It starts as a regular calculator without PIN setup dialogs. Keyboard input works.

Set your calculator password once in the private ZDesk dashboard. The backend
saves only a salted PBKDF2-HMAC-SHA256 verifier (210,000 iterations). All future
normal file downloads automatically append that configuration to the EXE.
Changing the password changes future downloads; existing files retain their
previous password. The Windows app opens as a regular calculator with no setup
prompt. Enter the password and press = to unlock the private window panel.
The 6–12 digit password is not sent to the backend in plaintext. The stored
verifier persists in the existing backend-only registry across server restarts.
The executable remains offline and uses the same 64-byte PIN format as v1.2.

Ctrl+Alt+Shift+R restores all hidden windows. Normal exit and the recovery monitor
also attempt restoration. If the hotkey or monitor is unavailable, hiding is
disabled. Apps remain visible in Task Manager and may re-show their own windows,
create notifications or play audio. This is window privacy, not an OS security
boundary. A person with control of your Windows account can bypass it.

Build locally with Start-System-Calculator.cmd, keeping the source and icon
beside it. The source can also be compiled with Mono mcs on Linux for Windows.
The Windows build workflow checks visible calculator startup, arithmetic,
configured-password unlock, hiding and restoring a test window, relocking and
crash recovery before publishing. Startup failures are logged to
%LOCALAPPDATA%\CalculatorVault\startup-error.log and displayed in an error dialog.

For the runtime-included build, use dotnet publish calculator/SystemCalculator.csproj
-c Release -o calculator-dist with .NET SDK 10. The source CMD launcher is an
alternative .NET Framework build for development.
