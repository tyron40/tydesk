# TyDesk v2 — Windows remote desktop development build

Original code with a browser controller, Windows companion, and self-hostable relay broker. This package expands the first TyDesk preview. It is NOT a tested, feature-complete replacement for RustDesk. Native Windows secure-desktop/pre-login support, video codecs/WebRTC, multi-monitor operation, installers/code signing, MFA and end-to-end encryption against the relay are not implemented.

## Implemented

- Browser device dashboard, screen viewing, mouse clicks, basic keys, ASCII text, scrolling and revocation.
- Persistent broker device registry in SQLite. The server stores a SHA-256 digest of each random device token, not the usable token.
- Opt-in saved enrollment protected by the current Windows user's DPAPI. After initial pairing, no new prompt is required when Remember this device is enabled.
- Opt-in Task Scheduler startup at Windows sign-in, in the current user's interactive desktop, with a visible companion window. Connection loss triggers retries when saved reconnect is enabled. Revoked credentials stop retries.
- System playback audio capture using WASAPI loopback through SoundCard, with browser playback. No microphone capture. Audio is sent as short stereo WAV chunks, with bounded latency/buffering.
- Bidirectional file transfer: browser uploads into `~/TyDesk/Inbox`; browser downloads only files the local user places in `~/TyDesk/Shared`. File transfers use a separate worker so they do not block screen uploads.
- Persistent enrollment/revocation/file/disconnect event history, viewable in the dashboard.
- Render Blueprint for HTTPS internet deployment with a persistent disk; Dockerfile and Docker Compose for self-hosting.

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

The current Windows user gets a named `TyDesk Remote Access Companion` scheduled task that starts the visible companion on sign-in. Keep the extracted project folder in place. Sign out and back in to test.

To remove automatic startup:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall-startup.ps1
```

Disconnect stops the current connection; it does not erase your saved enrollment. **Forget saved enrollment** erases the local credential. Also use dashboard **Revoke** to remove server authorization. Closing the companion stops it; it does not conceal itself or resist removal.

**This is not a system service. It cannot control Windows before sign-in, the lock screen, or UAC's secure desktop.** A native service and desktop-session integration are required for those capabilities. No Windows password is stored and Windows sign-in is not bypassed.

## Audio

Enable **Share system playback audio** locally. In the browser session, click **Listen to system audio**; browser playback requires that user gesture. It uses the default Windows output device. If the output device changes, toggle the local audio checkbox off/on. Capturing silence when no sound is playing is normal. SoundCard can fail on some Windows/audio driver combinations; device validation is required. Receiving audio through speakers while capturing the same device can cause feedback in a same-PC test; use separate devices/headphones or disable local listening.

## File exchange

Enable the local file permission. The companion creates `TyDesk/Inbox` and `TyDesk/Shared` in the Windows user's home directory. Use the browser file picker and **Send file** for uploads. For downloads, place a file directly inside Shared, click **Refresh files**, request it, then refresh shortly afterward for the Download button.

Limits: 20 MiB per file, 200 MiB aggregate broker storage, 100 outstanding transfer records, 200 published files per device, simple ASCII filenames. No arbitrary filesystem browsing, recursive directory download or automatic execution. Files are never intentionally overwritten; collisions use a transfer ID prefix. Transfers expire after an hour when the next file API operation runs, or are purged by revocation/disconnect. Restarting the broker clears temporary transfers; persistent device enrollment remains. Files are not malware-scanned. Permission changes stop new work; an HTTP upload already in flight may finish before disconnect completes. There is no resumed upload protocol.

## Internet hosting — Render

The source is published in the private repository https://github.com/tyron40/tydesk. The internet server has not been deployed. You do not need to run publish-github.ps1 for this repository.

Clone it on your Windows PC:

```powershell
git clone https://github.com/tyron40/tydesk.git
cd tydesk
code .
```

The Render workspace and hosting plan still need confirmation. The included render.yaml defines one Python web service, one instance, and a 1 GB persistent disk. Its compute and disk are paid resources; no paid service has been provisioned. The server password must be set privately as TYDESK_PASSWORD. A free test instance has ephemeral storage and loses enrollment when its filesystem resets.

Before Blueprint deployment, validate `render.yaml` with `render blueprints validate render.yaml` if the Render CLI is installed. Its public JSON schema was also checked during development; CLI/platform validation and an actual deploy are separate remaining checks. The Blueprint must be committed/pushed. In Render Dashboard, create a Blueprint from that repository, authorize Git access, review costs, supply the password, and apply. Render provides the HTTPS URL. Confirm `/health` responds, then use the URL as the companion Server URL and create a new pairing code there.

An internet deployment uses outbound HTTPS from the companion. No inbound router forwarding is required on the controlled Windows PC. HTTPS encrypts transport to the broker. The broker can read screen/audio/files; this is **not** RustDesk-style end-to-end encryption against the relay. Single-owner password access is implemented; individual accounts/MFA are not.

## Self-host instead

`compose.yaml` builds the broker and keeps its `/data` in a named volume. Set `TYDESK_PASSWORD` securely in your terminal environment, then run `docker compose up -d --build`. It binds only to loopback. For another computer, put an HTTPS reverse proxy in front or use a private network/VPN. The companion rejects plain HTTP other than loopback. Server process variables: `TYDESK_HOST`, `PORT` and `TYDESK_DATA`. Do not run multiple broker processes/replicas: frames, pairing codes and queues are memory-local. Compose/Docker builds were not executed in this environment.

## Validation and remaining gaps

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_server.py test_exchange.py
```

Nine tests cover auth, pairing, command validation, device token isolation, audio chunk transport/permission, SQLite token storage, disconnect/revocation, path traversal rejection, and bidirectional file delivery over real HTTP with temporary files. Python compilation and dashboard JavaScript syntax were checked.

These tests do not verify actual Windows capture/control, DPAPI, Task Scheduler startup, WASAPI audio drivers, browser audio playback, TLS proxy integration or an internet deployment. Those need your Windows machine and the hosted service. A full RustDesk replacement additionally needs native secure-desktop support, reliable encoding/streaming, keyboard layout handling, multi-monitor support, stronger authentication, E2EE, installation/signing, load/concurrency testing and an independent security review. Do not treat this development build as that finished product.

Primary display only; no drag gestures, held-key shortcuts, Ctrl+Alt+Delete, clipboard sync, Unicode typing or mobile companion. JPEG screen polling is a few frames per second. Device frames become unavailable after eight seconds offline. Existing viewers may retain their last displayed image until their next refresh. Move the local pointer to the top-left corner to trigger PyAutoGUI's emergency failsafe.

## License and references

Original TyDesk source: MIT; dependencies have their own licenses. Not affiliated with RustDesk.

- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks
- https://soundcard.readthedocs.io/en/latest/
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
