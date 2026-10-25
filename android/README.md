# ZDesk Android development companion

Android 8+ (API 26), target/compile API 35. Java 17, Gradle 8.11.1, Android Gradle Plugin 8.9.2. GitHub Actions runs unit tests and lint, builds a debug-signed APK, verifies its signature and publishes downloads/ZDesk-Android.apk. Download endpoint: /download/android.

Screen capture requires Android MediaProjection approval for each session. The foreground sharing notification has a Stop action. No boot-time capture, lock-screen bypass or hidden restart is implemented. Leaving setup keeps only the already approved foreground session active. Android may stop sharing when locked or under resource/battery restrictions.

Microphone sharing is separately selected and requires Android runtime permission. Saved pairing uses AES-GCM with an Android Keystore key; app backup is disabled. Forget removes local credentials; also revoke old devices in the dashboard. A new connection code overrides existing enrollment.

Remote control additionally requires locally enabling the disclosed AccessibilityService. Commands are gated on active projection, local control permission and an active session. Supports taps, long presses, drag on release, swipes, back and basic text/clipboard actions. Password fields are not edited. Windows-style hover, arbitrary shortcuts and secure-screen interaction are not implemented.

File access is limited to user-selected document URIs and the app's private Inbox, with 20 MB limits. Incoming files are exported using the user's Save document picker. No broad storage access or automatic execution.

This first APK is a development build, not a Play Store production release. A stable private release signing key must be configured for reliable long-term updates. A changed development key requires reinstalling, which removes local pairing. Review Android's installation and accessibility permission screens; do not disable security protections.

Build: gradle :app:testDebugUnitTest :app:lintDebug :app:assembleDebug. Hardware screen capture, OEM accessibility and audible microphone playback still require real-device testing.
