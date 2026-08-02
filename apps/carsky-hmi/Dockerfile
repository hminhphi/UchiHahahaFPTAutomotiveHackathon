FROM gradle:8.10.2-jdk17 AS builder

LABEL org.opencontainers.image.title="FleetIQ CarSky Android HMI builder"

ARG ANDROID_CLI_TOOLS=11076708
ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" \
    && curl -fsSL \
      "https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_CLI_TOOLS}_latest.zip" \
      -o /tmp/android-tools.zip \
    && unzip -q /tmp/android-tools.zip -d /tmp/android-tools \
    && mv /tmp/android-tools/cmdline-tools "${ANDROID_HOME}/cmdline-tools/latest" \
    && rm /tmp/android-tools.zip
RUN yes | "${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null \
    && "${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager" \
      "platform-tools" "platforms;android-35" "build-tools;35.0.0"

WORKDIR /workspace
COPY settings.gradle.kts build.gradle.kts gradle.properties ./
COPY app/build.gradle.kts app/build.gradle.kts

COPY app app
RUN gradle --no-daemon testDebugUnitTest assembleDebug

FROM scratch
COPY --from=builder /workspace/app/build/outputs/apk/debug/app-debug.apk /fleetiq-carsky-hmi.apk
