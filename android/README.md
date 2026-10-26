# ZDesk Android development companion

Android 8+ (API 26), target/compile API 35. Java 17, Gradle 8.11.1, Android Gradle Plugin 8.9.2. GitHub Actions runs unit tests and lint, builds a debug-signed APK, verifies its signature and publishes downloads/ZDesk-Android.apk. Download endpoint: /download/android.

Screen capture requires Android MediaProjection approval for each session. The foreground sharing notification has a Stop action. No boot-time capture, lock-screen bypass or hidden restart is implemented. Leaving setup keeps only the already approved foreground session active. Android may stop sharing when locked or under resource/battery restrictions.

Microphone sharing is separately selected and requires Android runtime permission. Saved pairing uses AES-GCM with an Android Keystore key; app backup is disabled. Forget removes local credentials; also revoke old devices in the dashboard. A new connection code overrides existing enrollment.

Remote control additionally requires locally enabling the disclosed AccessibilityService. Commands are gated on active projection, local control permission and an active session. Supports taps, long presses, drag on release, swipes, back and basic text/clipboard actions. Password fields are not edited. Windows-style hover, arbitrary shortcuts and secure-screen interaction are not implemented.

File access is limited to user-selected document URIs and the app's private Inbox, with 20 MB limits. Incoming files are exported using the user's Save document picker. No broad storage access or automatic execution.

This first APK is a development build, not a Play Store production release. A stable private release signing key must be configured for reliable long-term updates. A changed development key requires reinstalling, which removes local pairing. Review Android's installation and accessibility permission screens; do not disable security protections.

Build: gradle :app:testDebugUnitTest :app:lintDebug :app:assembleDebug. Hardware screen capture, OEM accessibility and audible microphone playback still require real-device testing.

## Dashboard uninstall requests

Version 1.1 advertises uninstall support while sharing with control enabled. The dashboard device card and session toolbar can request removal. Open ZDesk or tap its active notification within two minutes to review the request. Android shows its normal uninstall confirmation after ZDesk stops capture and disables its accessibility service. Cancelling keeps the app installed; start sharing again if desired. Android uninstallation removes private app data and received Inbox files, so export received files first. Revoke the dashboard pairing after verifying removal. Offline devices and older builds cannot receive uninstall requests.

Version 1.2 adds front/rear camera sharing with explicit local choice each session. The foreground service declares the camera type and starts only after OS permission while the setup Activity is visible. The active notification identifies camera sharing. Stop camera or Stop sharing releases the Camera2 session. Android 13+ notification permission is required when sharing a camera. Camera capture is never auto-enabled by saved pairing. Physical device compatibility, orientation and OEM camera behavior still require real-device validation.
