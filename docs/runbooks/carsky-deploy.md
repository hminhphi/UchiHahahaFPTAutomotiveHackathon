# CarSky Deployment Runbook

This runbook follows the organizer's
[`Car-Sky-Platform.html`](../reference/carsky/Car-Sky-Platform.html) lifecycle:
Blueprint -> Deploy -> Room -> Device -> Widget.

## 1. Build and push artifacts

1. Build the HMI APK with `apps/carsky-hmi/Dockerfile` and publish the resulting
   `fleetiq-carsky-hmi.apk` as an Artifact in CarSky.
2. Build the Container Node with `carsky/bridge/Dockerfile`, tag it
   `<ZOT_HOST>/fleetiq/carsky-coaching-bridge:<version>`.
3. In CarSky Registry, create a Zot API key, log Docker into the displayed Zot
   hostname, push the bridge image and verify the tag is visible.
4. Register the organizer Android Automotive image and the FleetIQ VSS schema
   under Artifacts. Record immutable artifact IDs; do not place API keys in the
   blueprint.

## 2. Create the blueprint

1. Open Nydus and import `carsky/blueprint.example.json`.
2. Replace every angle-bracket placeholder with the tenant's immutable Zot and
   Artifact IDs.
3. Verify these nodes exist: Container `coaching-bridge`, KUKSA Broker
   `vehicle-signals`, Skycraft `fleetiq-aaos`, and Ethernet Bridge `room-l2`.
4. Verify bridge, broker and Android guest share the Ethernet Bridge.
5. Verify the coaching KUKSA output reaches the broker and the Android
   KUKSA/VHAL input. Use
   `Vehicle.Cabin.Infotainment.HMI.CurrentCommand` for the approved custom VSS
   branch.
6. Attach a Screen widget to `fleetiq-aaos.screen`.

The JSON is a topology template. Nydus may regenerate tenancy-specific IDs or
pin metadata when it imports the blueprint; review the canvas before deploy.

## 3. Deploy and attach

1. Select **New Deployment**, choose or create the Android test device and
   deploy the blueprint.
2. Wait until every node reports `Running`. For `ImagePullBackOff`, recheck the
   Zot hostname/tag and cluster pull permission.
3. Open the deployment details and record the Room namespace/ID.
4. Under Devices, attach the Skycraft guest to that Room.
5. Open the Screen widget and confirm Android Automotive boots into
   `FleetIQ Guardian`.
6. Open the bridge health conduit:
   `https://<host>/conduit/http/<room>/<coaching-bridge>/8090/health`.
7. Send one severity-5 fixture, verify the short action phrase appears, press
   **ACKNOWLEDGE**, and verify the bridge returns `acknowledged: true`.

## 4. Production connection

Configure the coaching worker with the CarSky HTTPS base URL, API key, Room ID
and bridge node key. Keep the API key in the platform secret store. Do not bake
it into the APK, image or blueprint. The worker's `Idempotency-Key` and the
bridge `dedupe_key` prevent duplicate driver prompts.

## 5. Rollback

1. Stop remote delivery and select `MockCarSkyAdapter` in the coaching worker.
2. Keep the current Room alive long enough to verify no new prompts arrive.
3. Roll the bridge image back to the previous immutable Zot tag, or teardown
   the deployment if the Room is unhealthy.
4. Re-deploy the last known-good blueprint and reattach the Screen widget.
5. Preserve event/command IDs in the incident note; never include CarSky API
   keys or raw request headers.
