# FleetIQ CarSky HMI

Android Automotive coaching surface for the CarSky Skycraft guest. The screen
shows only severity, one bounded action phrase, connection state and driver
acknowledgement. Detailed evidence and model confidence remain in the web
operations console.

## Build

The reproducible builder requires:

- Docker daemon with outbound access to `dl.google.com`, Google Maven and Maven
  Central.
- Android SDK platform 35 and build tools 35.0.0.
- Gradle 8.10.2, Android Gradle Plugin 8.7.3 and JDK 17.

Build the APK artifact:

```text
docker build -f apps/carsky-hmi/Dockerfile apps/carsky-hmi
```

For a local Android SDK, run `gradle testDebugUnitTest assembleDebug` from this
folder. Set `-PFLEETIQ_BRIDGE_URL=http://<bridge-host>:8090` when the CarSky room
does not resolve the emulator default `10.0.2.2`.

The local workstation currently has no Android SDK/Gradle installation, and its
Docker daemon must be running before either build path can be verified.
