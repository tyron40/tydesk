# System Calculator 2.0

Open System Calculator.exe on 64-bit Windows 10/11. The published single EXE
includes its .NET runtime; no separate .NET installation is needed.
It starts as a scientific calculator without PIN setup dialogs. Keyboard input works.
Scientific functions include degrees/radians, trigonometry, square root, powers,
logarithms, factorial, reciprocal, constants and parentheses. Unary function
buttons act on the current expression; x^y inserts a power operator.

After password + equals, the redesigned private dashboard contains:
- Windows: hide and restore running windows.
- Persistent sidebar: running/hidden window selectors, Refresh windows, Hide window,
  Restore window and Restore all windows stay available on Files and Apps pages.
- Files: drives, Home/Desktop/Documents/Downloads shortcuts, editable folder path,
  parent navigation, double-click/open selected and Open in Explorer.
- Apps: searchable Start menu programs, launch selected, browse for an executable,
  and All Windows apps (the Windows applications folder, including Store apps).

Files > Hide selected moves files/folders out of their original locations into
private storage. Hidden files/apps is a dedicated sidebar page with the original
path, item type and status, Open hidden item, Restore selected, and Restore all.
Restoration never overwrites an existing item. Rename/move any conflicting item
and try again. Items are not automatically restored when the calculator closes.

Storage is in %LOCALAPPDATA%\CalculatorVault\Storage on the system data drive.
Other drives use a hidden .SystemCalculatorStorage-<user id> directory on that
same drive. Moves use Windows MoveFileEx without copy/delete or overwrite flags.
If that storage location cannot be created or Windows denies the move, the item
stays where it was and an error is shown. Originals and stored items are not
deleted to resolve errors. Keep storage on removable drives connected to restore
those items. The recovery journal is saved before moving each item.

Apps > Hide app shortcut moves the selected .lnk or .appref-ms into storage and
removes that shortcut from its original Start menu/Desktop folder. The installed
program, other shortcuts, Settings entry and Task Manager process remain. Open
hidden item launches the stored shortcut; Restore selected puts it back. Installed
program directories are never moved. Portable folders can be moved from Files,
but should not be running when moved. System paths, calculator data, and reparse
points are not moved.

Version 1.9 hidden-attribute records are imported as old hidden items. Select them
in Hidden files/apps and choose Move old hidden items, or Restore selected to
remove the old Hidden attribute. Upgrading does not silently relocate old data.

Storage is not encrypted and is not an OS security boundary. File access follows
the current Windows account permissions. File/folder contents and attributes are
preserved. ZDESK_CALCULATOR_DATA_DIR may override the local data directory for
isolated automated tests; normal downloads use the default path.

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
