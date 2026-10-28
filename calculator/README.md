# System Calculator 1.2

Open System Calculator.exe on Windows 10/11 with .NET Framework 4.7.2 or newer.
It starts as a regular calculator without PIN setup dialogs. Keyboard input works.

To configure the private window panel:
1. Sign in at https://zdesk-nnym.onrender.com/#calculator-settings.
2. In System Calculator PIN, enter and repeat 6–12 digits.
3. Click Set PIN & download app.
4. Close the old calculator and open the newly downloaded System Calculator.exe.
5. Enter your PIN and press = to unlock the panel.

Changing the PIN requires a fresh configured download. Previously downloaded
copies retain their own PIN. The website does not remotely change a running app.
PIN preparation happens in the browser using PBKDF2-HMAC-SHA256, 210,000 iterations
and a random 16-byte salt. A 64-byte configuration (salt, 32-byte hash, format
marker ZDESKCALCPIN0002) is appended to the unsigned EXE. The plaintext PIN is
not sent to the server or saved in browser storage. A generic download has no
configured PIN; legacy local DPAPI PIN settings remain supported.

Ctrl+Alt+F12 restores all hidden windows. Normal exit and the recovery monitor
also attempt restoration. If the hotkey or monitor is unavailable, hiding is
disabled. Apps remain visible in Task Manager and may re-show their own windows,
create notifications or play audio. This is window privacy, not an OS security
boundary. A person with control of your Windows account can bypass it.

Build locally with Start-System-Calculator.cmd, keeping the source and icon
beside it. The source can also be compiled with Mono mcs on Linux for Windows.
Compiled and PIN format interoperability tested on Linux; Windows UI, hotkeys
and recovery behavior need testing on a Windows machine.
