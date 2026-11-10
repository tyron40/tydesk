## Android browser companion and multiple sessions

Android browsers can share an explicitly permitted microphone and user-selected files while the page remains open. Screen sharing is offered only where getDisplayMedia exists; Chrome Android does not supply it. This browser companion cannot control Android apps or run unattended. Full Android remote screen/control requires a native Android app and is not implemented here. File transfers are limited to 20 MB and selected filenames; incoming files are saved by clicking a visible download link.

For several computers, use Open in new window on each online device card. Each window has independent screen, input, audio and file UI. Browsers may open tabs instead or block pop-ups; open one window per click. Credentials are handed only to registered same-origin child windows in memory, never URL parameters or browser storage. Locking the parent dashboard locks its child session windows.

## Microphone sharing (3.2)

The Windows companion has separate **System playback audio · PC sounds** and **Microphone · surrounding sound** checkboxes. Microphone access defaults off. Enabling it requires local confirmation; remembered microphone permission is stored only when Remember this computer is selected. The default Windows input device is used. Enable either source or both, then click **Listen to shared audio** in the dashboard. Windows desktop microphone permission and a working physical input device are required. Uncheck Microphone, Disconnect, or Quit ZDesk to stop microphone sharing. An in-flight audio upload cannot be recalled.

# ZDesk v2 — Windows remote desktop development build

Original code with a browser controller, Windows companion, and self-hostable relay broker. This package expands the first ZDesk preview. It is NOT a tested, feature-complete replacement for RustDesk. Native Windows secure-desktop/pre-login support, video codecs/WebRTC, multi-monitor operation, installers/code signing, MFA and end-to-end encryption against the relay are not implemented.

## Dashboard 3.1: mouse, touch and system audio

Download the updated companion to enable protocol 2. The dashboard detects older companions and offers an update link; basic clicks remain compatible.

Desktop control supports live pointer movement and cursor shape, left/right click, drag, wheel scrolling, focused keyboard input and common Ctrl shortcuts. Commands are batched, mouse movements are coalesced, and input polling runs independently of screen capture. Held buttons/keys are released on lost input, permission changes and disconnect; the companion applies a short hold lease.

Phone/tablet layouts include larger controls, direct touch, tap, drag, hold-and-lift for right-click, two-finger scroll, relative trackpad mode, a keyboard text field, screen zoom and a fullscreen fallback. Pan / zoom view disables remote touch input so you can move the viewport. Browser/device combinations still require physical touch validation.

System playback capture runs continuously while a separate bounded queue uploads short PCM WAV chunks. The browser plays PCM through Web Audio with volume, a level meter, resume handling and explicit silence/error status. The capture source remains the default Windows playback device, a physical microphone only when its separate local permission is enabled. Play sound on that output device and enable system audio sharing locally before pressing Listen.

Validation includes 31 Python tests and browser logic tests for mouse/touch gestures, key release, a known audio tone, PCM decoding, playback scheduling, resume, volume and stop. Mocked and transport checks do not prove Windows audio drivers, audible phone output or physical touch behavior. Live screen polling is still JPEG over HTTPS, with network-dependent latency; no video codec/WebRTC or secure desktop support was added.

## Companion 3.0: reusable passcode and tray mode

The updated Windows companion uses a dark interface with connection, permission, and startup sections. A newly entered code always overrides an old saved enrollment. A revoked credential is cleared locally and prompts for a new connection; it is never silently re-enrolled.

In the signed-in dashboard, use **One passcode. Your computers.** to set a reusable connection passcode of 16–128 characters. Paste it into each companion once and enable **Remember this computer and reconnect automatically**. One-use codes remain available. The server stores a salted PBKDF2 hash, limits enrollment attempts, and retains settings in the protected durable registry. Rotation/disable affects future enrollment; existing devices must be explicitly revoked.

Enable **Keep available in the tray when I close this window** for window-close background access. The visible tray menu offers Open, Connect, Disconnect and Quit. Reopening the desktop shortcut brings back the existing window. Disconnect stops access; Quit stops the app. Enable sign-in startup separately for availability after Windows sign-in. The computer must stay awake; this does not add pre-login, lock-screen or UAC access.

## Standalone Windows application

Download https://zdesk-nnym.onrender.com/download/windows to get **ZDesk.exe** (Windows x64). No Python or VS Code is required. Save the EXE in a permanent folder and double-click it to open the companion connection page. It is unsigned. Use **Add ZDesk desktop shortcut** to create a desktop icon; keep the EXE in place afterward.

Pair once using a dashboard code and select **Remember this computer and reconnect automatically**. The local enrollment is encrypted with Windows DPAPI. Future app launches reconnect with it without another pairing code. Enable sign-in startup for automatic launch when this Windows user signs in. The app stays available as a window or an opted-in tray icon, with Disconnect and Forget controls. Offline devices stay in the dashboard as long as the device registry is retained.

**Permanent device storage is configured.** Render uses a protected Supabase registry in isolated ZDesk tables in the existing motivation project. Device identities and token hashes survive free-server filesystem resets; raw enrollment tokens stay on the Windows device. The unused extra database project was deleted. No additional database project or paid Render disk was added. Usage counts toward the existing account's allowances.

The EXE was built on a Windows runner. The packaged app passed its Tk startup and DPAPI round-trip self-test. The live downloaded binary's SHA-256 was checked against downloads/windows-build.json. Physical Windows capture, audio hardware and sign-in startup still require testing on your PC.

Source download remains at https://zdesk-nnym.onrender.com/download/windows-source for users who prefer Python.

## Implemented

- Browser device dashboard, screen viewing, mouse clicks, basic keys, ASCII text, scrolling and revocation.
- Persistent broker device registry backed by Supabase on the hosted service, with SQLite as the local cache. The server stores a SHA-256 digest of each random device token, not the usable token.
- Opt-in saved enrollment protected by the current Windows user's DPAPI. After initial pairing, no new prompt is required when Remember this device is enabled.
- Opt-in Task Scheduler startup at Windows sign-in, in the current user's interactive desktop, with a companion window or opted-in tray icon. Connection loss triggers retries when saved reconnect is enabled. Revoked credentials stop retries.
- System playback audio capture using WASAPI loopback through SoundCard, with browser playback. Separate opt-in microphone capture is available in version 3.2. Audio is sent as short stereo WAV chunks, with bounded latency/buffering.
- Bidirectional file transfer: browser uploads into `~/ZDesk/Inbox`; browser downloads only files the local user places in `~/ZDesk/Shared`. File transfers use a separate worker so they do not block screen uploads.
- Persistent enrollment/revocation/file/disconnect event history, viewable in the dashboard.
- Free-plan Render deployment configuration; Dockerfile and Docker Compose for self-hosting.

## Browser companion and download choices

Open https://zdesk-nnym.onrender.com/companion on the computer you want to share. Create a pairing code from the signed-in dashboard, paste it into the browser companion, click Share this computer, and select a screen/window/tab in the browser's picker. The screen appears in the dashboard as a view-only device. Stop sharing from the page or the browser's own sharing indicator. Keep the page open; background throttling may slow updates.

Browser mode has no OS mouse/keyboard control, system audio, file exchange or unattended startup. Screen-capture support varies by browser; unsupported browsers show an explanation. Screen permission is requested each time and capture is not saved across reloads. Browser sharing needs an actual desktop-browser/device test; server route and download tests do not prove screen capture works on every platform.

For native features, use Download ZDesk for Windows on that page or https://zdesk-nnym.onrender.com/download/windows. The source alternative is https://zdesk-nnym.onrender.com/download/windows-source. The source ZIP contains the companion source and Start-ZDesk.cmd; it does not redirect to GitHub. To use the source alternative, extract all files, install Python 3.12 or 3.13 with its launcher and Tcl/Tk, and double-click Start-ZDesk.cmd. The standalone EXE requires no Python; both versions default to the hosted server. The download contains no passwords, enrollment credentials, or server data.

## Pair from PowerShell on Windows

Download and extract the [Windows source ZIP](https://zdesk-nnym.onrender.com/download/windows-source), install Python 3.12 with the Windows launcher and Tcl/Tk, and open regular PowerShell in the extracted ZDesk-Companion folder. Quit any running ZDesk instance first.

```powershell
.\start-agent.ps1 -TerminalSetup
```

Choose the optional sharing features, enter the masked ZDesk pairing code or connection passcode, and type `CONNECT` after checking the sharing summary. ZDesk opens a visible window with a Disconnect button. Terminal setup does not start at sign-in or run in the tray on close. To opt in to remembering the pairing, run `.\start-agent.ps1 -TerminalSetup -RememberPairing`. Enter the code on the first run; later runs with the same switch reuse the device token protected by Windows DPAPI. They still show the sharing summary and require `CONNECT`. The passcode and sharing choices are not saved. Use **Forget this computer** from that session to remove its saved terminal pairing. The portable, windowed EXE still uses its own pairing screen. Do not put your Windows password or ZDesk code into the command.

To preselect every available sharing feature from PowerShell, add `-AllSharing`. With the direct Python command, use `--terminal-setup --remember-pairing --all-sharing`. Review the printed sharing summary, enter the pairing code at the masked prompt if needed, and type `CONNECT` to begin. This does not grant Windows administrator privileges or change Windows privacy settings.

To start without opening the main window, add `-StartInTray` (Python: `--start-in-tray`). PowerShell still displays the sharing summary and requires local confirmation. The visible ZDesk tray icon must start before sharing can begin and offers Open ZDesk, Disconnect and Quit. If the icon cannot start, the window opens and sharing does not begin. This is for a signed-in Windows session; it does not bypass sign-in or Windows security settings. No new pairing-code generation is involved.

### Foreground console session

Run `.\start-agent.ps1 -Console -AllSharing -RememberPairing` from an interactive, regular Windows PowerShell session. The direct Python form is `.\.venv\Scripts\python.exe agent.py --terminal-setup --console --all-sharing --remember-pairing`. Enter the existing pairing code at the masked prompt, review the local sharing summary, and type `CONNECT`.

This mode does not create a Tk window or tray icon: the visible terminal identifies ZDesk, reports connection and capture status, and provides Ctrl+C to stop. Keep the terminal open. It uses the same capture, input validation and selected-feature checks as the desktop app, while storing only the optional Windows-protected device credential. It does not install a service, enable sign-in startup, disguise itself, grant administrator privileges, or modify Windows privacy/security settings. Uninstall requests require the ordinary companion.

## Windows quick start (VS Code → Terminal → PowerShell)

Install Python 3.12 or 3.13 from python.org, including its launcher and Tcl/Tk. Extract the ZIP and open its `tydesk` folder in VS Code.

Start the broker:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-server.ps1
```

Choose a unique server password of at least 16 characters. Keep that terminal running. Open http://127.0.0.1:8787 in your browser, enter that password, and click **Pair a computer**.

Start the companion in another terminal:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-agent.ps1
```

Paste the pairing code; the default server URL is correct for this same-PC test. Check the permissions you want, press Start, and accept sharing. Open the device from the dashboard. Viewing your own screen can create a mirror effect.

The scripts' ExecutionPolicy Bypass applies only to that invocation. They do not permanently change Windows execution policy. Dependencies install into `.venv`. The server requires only `requirements-server.txt`; the Windows companion uses `requirements.txt`.

## Unattended reconnect after Windows sign-in

1. Pair the companion once and enable the desired control, audio and file checkboxes.
2. Enable **Remember this device and reconnect without another prompt** and accept its explanation. Changes to permissions are saved with the enrollment.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-startup.ps1
```

The current Windows user gets a named `ZDesk Remote Access Companion` scheduled task that starts the visible companion on sign-in. Keep the extracted project folder in place. Sign out and back in to test.

To remove automatic startup:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall-startup.ps1
```

Disconnect stops the current connection; it does not erase your saved enrollment. **Forget saved enrollment** erases the local credential. Also use dashboard **Revoke** to remove server authorization. Closing the window keeps it running only when tray mode is enabled. Quit ZDesk stops the application.

**This is not a system service. It cannot control Windows before sign-in, the lock screen, or UAC's secure desktop.** A native service and desktop-session integration are required for those capabilities. No Windows password is stored and Windows sign-in is not bypassed.

## Audio

Enable **Share system playback audio** locally. In the browser session, click **Listen to system audio**; browser playback requires that user gesture. It uses the default Windows output device. If the output device changes, toggle the local audio checkbox off/on. Capturing silence when no sound is playing is normal. SoundCard can fail on some Windows/audio driver combinations; device validation is required. Receiving audio through speakers while capturing the same device can cause feedback in a same-PC test; use separate devices/headphones or disable local listening.

## File exchange

Enable the local file permission. The companion creates `ZDesk/Inbox` and `ZDesk/Shared` in the Windows user's home directory. Use the browser file picker and **Send file** for uploads. For downloads, place a file directly inside Shared, click **Refresh files**, request it, then refresh shortly afterward for the Download button.

Limits: 20 MiB per file, 200 MiB aggregate broker storage, 100 outstanding transfer records, 200 published files per device, simple ASCII filenames. No arbitrary filesystem browsing, recursive directory download or automatic execution. Files are never intentionally overwritten; collisions use a transfer ID prefix. Transfers expire after an hour when the next file API operation runs, or are purged by revocation/disconnect. Restarting the broker clears temporary transfers; persistent device enrollment remains. Files are not malware-scanned. Permission changes stop new work; an HTTP upload already in flight may finish before disconnect completes. There is no resumed upload protocol.

## Internet hosting — Render

ZDesk is deployed at **https://zdesk-nnym.onrender.com/** on Render's **free** compute plan in My Workspace. Source: private repository https://github.com/tyron40/tydesk. No paid compute or persistent disk was provisioned.

### Use the hosted server from Windows

```powershell
git clone https://github.com/tyron40/tydesk.git
cd tydesk
powershell -ExecutionPolicy Bypass -File .\\start-agent.ps1
```

Open the hosted dashboard. Retrieve your server password from Render Dashboard → tydesk-broker → Environment → TYDESK_PASSWORD. It is deliberately not committed to source or repeated here. Unlock the dashboard and select Pair a computer. In the Windows companion, enter https://zdesk-nnym.onrender.com as Server URL, paste the pairing code and enable the desired permissions. No local server is needed when using the hosted service.

The live HTTPS deployment was checked for authentication rejection, authenticated pairing, frame transport, command delivery, audio chunk transport, bidirectional file transfer and revocation. The temporary check device was removed. These are server transport checks, not tests of Windows hardware or browser audio playback.

### Free-tier constraints

The server uses an ephemeral filesystem with no disk. Temporary files and active sessions are lost when Render resets that filesystem. Saved device identities and authorization hashes are restored from the separate durable registry; remembered native companions can reconnect using their existing credentials. Free services spin down after inactivity and take time to wake; usage limits are shared with the workspace's other free services. Bandwidth and build usage are metered at workspace level; exceeding included allowances can cause suspension or supplementary charges depending on account billing settings. This is a free-plan test deployment, not guaranteed zero-cost unlimited hosting or reliable always-on unattended access.

The included render.yaml now matches free hosting, with no persistent disk. It declares the password as a secret placeholder and never embeds its value. The created service is managed directly in Render; do not apply a separate Blueprint to the same service without reviewing its settings.

An internet deployment uses outbound HTTPS from the companion. No inbound router forwarding is required on the controlled Windows PC. HTTPS encrypts transport to the broker. The broker can read screen/audio/files; this is **not** end-to-end encryption against the relay. Single-owner password access is implemented; individual accounts/MFA are not.

## Self-host instead

`compose.yaml` builds the broker and keeps its `/data` in a named volume. Set `TYDESK_PASSWORD` securely in your terminal environment, then run `docker compose up -d --build`. It binds only to loopback. For another computer, put an HTTPS reverse proxy in front or use a private network/VPN. The companion rejects plain HTTP other than loopback. Server process variables: `TYDESK_HOST`, `PORT` and `TYDESK_DATA`. Do not run multiple broker processes/replicas: frames, pairing codes and queues are memory-local. Compose/Docker builds were not executed in this environment.

## Validation and remaining gaps

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_server.py test_exchange.py test_browser.py
```

Twelve tests cover auth, pairing, command validation, device token isolation, audio chunk transport/permission, SQLite token storage, disconnect/revocation, path traversal rejection, and bidirectional file delivery over real HTTP with temporary files, browser-page availability, credential-free download contents, and revoked browser pairing behavior. Python compilation and dashboard JavaScript syntax were checked. Live registry write/read, wrong-key rejection and deletion passed. A separate integration check restarted the broker against two fresh filesystems and verified saved-device recovery, authentication with the existing token, and revocation surviving another restart.

These tests do not verify actual Windows capture/control, DPAPI, Task Scheduler startup, WASAPI audio drivers, browser audio playback, or a real Windows-to-browser internet session. Those need your Windows machine and the hosted service. A full RustDesk replacement additionally needs native secure-desktop support, reliable encoding/streaming, keyboard layout handling, multi-monitor support, stronger authentication, E2EE, installation/signing, load/concurrency testing and an independent security review. Do not treat this development build as that finished product.

Primary display only; no Ctrl+Alt+Delete, clipboard sync, Unicode typing or mobile companion. JPEG screen polling is a few frames per second. Device frames become unavailable after eight seconds offline. Existing viewers may retain their last displayed image until their next refresh. Move the local pointer to the top-left corner to trigger PyAutoGUI's emergency failsafe.

## License and references

Original ZDesk source: MIT; dependencies have their own licenses. Not affiliated with RustDesk.

- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks
- https://soundcard.readthedocs.io/en/latest/
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata

The branded address is a free gateway to the original authoritative broker. Existing companions configured with https://tydesk-broker.onrender.com continue to work, and all devices use the same dashboard registry and session state. The gateway and broker share the Render workspace free compute-hour and bandwidth allowances.

### Remove a companion

Update the native companion, connect with local control enabled, then select **Uninstall companion** on the device card or session toolbar. Android requests confirmation in the visible app and its system uninstaller. Windows confirms before disabling startup, removing desktop shortcuts and saved enrollment, then recycling the running portable EXE after exit. It preserves shared and received PC files. Revoke the dashboard pairing after verifying removal; revocation alone does not uninstall software. Offline devices and browser companions cannot be uninstalled from the dashboard.

### Camera sharing (Windows 3.6 / Android 1.4)

ZDesk stays visibly named as a remote-access companion. Enable Camera on the device, then use Open camera view in the dashboard session. The viewer cannot activate a camera. Windows automatically tries the default camera, alternate Windows capture backends and available devices. Camera selection is saved with remembered pairing and resumes on reconnect, including optional sign-in startup. Inline permission descriptions explain this; Stop camera clears the saved choice, while Disconnect ends the current capture. Android offers front/rear selection, an OS camera permission prompt, a foreground camera notification and Stop camera / Stop sharing; notifications are required for camera sharing on Android 13+. Android remembers the camera/front-rear selection for the next local Start; camera sharing must still start from the visible app. No dashboard camera-enable command is available.

Camera JPEG frames are kept only as a current in-memory frame, require the device token to upload and dashboard authentication to view, expire after eight seconds, and are cleared when permission is disabled or the device disconnects. No camera recording is implemented. Some protected camera hardware, privacy switches or another app owning the camera can prevent capture. Build and mock transport checks do not substitute for testing on actual devices.

Mobile expanded sessions use native fullscreen when available and a safe-area-aware full-window layout otherwise. Controls reveals touch mode, zoom, camera/audio and file tools. Fit screen preserves pointer coordinates without letterbox offsets; trackpad supports hold-then-drag, two-finger scrolling and jitter filtering.

Select all sharing features selects the locally available camera, audio, control and file options. It does not enable sign-in startup or tray behavior, bypass Accessibility setup, or start a disconnected companion. Custom repeated permission dialogs are replaced by inline explanations; OS permissions, active sharing indicators, Stop controls and uninstall confirmation remain. Android notification updates alert only once.


### Desktop downloads by operating system and processor

Open `/downloads` for a single brand-independent catalog: Windows Intel/AMD x64, macOS 15+ Intel and Apple Silicon, Linux X11 Intel/AMD x64 and ARM64 (Ubuntu 22.04+ / glibc 2.35+), plus Android. Links only become available once a corresponding artifact exists. `/api/downloads` includes an allowlisted catalog, availability, version and checksum when published. Downloads are served directly by the ZDesk website, with no GitHub redirect.

Mac and Linux native apps share the same visible UI, pairing, local camera/microphone choices, input protocol, files and dashboard sessions. Mac permissions must be enabled locally in System Settings; microphone works through CoreAudio, but system playback loopback is not included. Linux uses X11 capture and input, with PulseAudio / PipeWire Pulse compatibility for audio. Wayland whole-desktop control, Alpine/musl, obsolete 32-bit desktops, legacy macOS and native Windows ARM are outside these build targets. ChromeOS uses browser sharing with its existing limits; there is no native ChromeOS unattended-control app.

Saved Windows enrollment stays DPAPI-protected. Mac and Linux enrollment uses the OS Keychain, Secret Service or KWallet and refuses plaintext storage. If the secure store is absent or locked, manual pairing remains available; remembered pairing requires unlocking/configuring the secure store. Login startup and shortcuts are explicit local actions and run as the signed-in user. Remote uninstall is still advertised only by the Windows and Android builds that implement it.

The Mac/Linux workflow builds on each matching OS and CPU, runs platform tests and exercises the actual packaged UI without requesting capture permissions, before publishing downloads. Mac bundles are ad-hoc signed development apps, not Apple-notarized releases. These automated tests do not certify every laptop model, camera, audio driver, display setup or restricted device. Hardware testing is still required.


### Microphone continuity (desktop 3.8 / Android 1.5)

Capture now keeps a bounded three-second queue instead of replacing pending microphone audio. Desktop, Android and browser companions combine consecutive chunks into up-to-one-second WAV uploads, reducing round-trip overhead while preserving sample order. Desktop capture diagnostics use a separate connection so a slow status request cannot block sound uploads.

The broker accepts valid stereo 24 kHz / 16-bit PCM batches up to two seconds, and retains only a bounded current four-second memory window. The dashboard consumes every pending sequence instead of keeping just the final three packets. Playback starts with an 800 ms jitter buffer and adapts up to 1.4 seconds after an underrun. It does not acknowledge packets that have not been scheduled. Initial listening starts near live sound, and stopping sharing clears pending queues; no audio recording is added. A sustained network outage can still interrupt playback.

Regression tests simulate slow status requests, queued upload bursts and variable playback arrival times, verify contiguous playback schedules, batch sample order, stale/disabled-source rejection and Android queue bounds. Actual microphone hardware and the user's connection still need listening tests.

Audio responses also include a per-stream identifier. Dashboard playback resets its sequence tracking after a broker restart, so a restarted server cannot leave the listener waiting for an old sequence counter to catch up.


### Dashboard audio recording

After Listen, choose Record audio, then Stop recording and Download recording. The browser records the remote playback graph, including volume adjustments, silence and network interruptions; it never requests the dashboard device microphone. Supported formats are selected at runtime (WebM/Opus, MP4 audio or Ogg, with browser default fallback). Unsupported browsers show an inline error. Recordings stay in browser memory, with a 64 MB / one-hour cap, and are not uploaded to the broker. Download before refreshing or leaving. Stopping listening, hiding the tab or switching devices finalizes the recording; switching devices cannot mix two devices in one recording. Discard releases the saved blob URL. This records the existing buffered transport; WebRTC is still pending.
