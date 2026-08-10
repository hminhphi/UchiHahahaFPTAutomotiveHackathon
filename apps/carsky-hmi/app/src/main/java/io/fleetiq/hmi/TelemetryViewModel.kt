package io.fleetiq.hmi

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

data class TelemetryState(
    val speedKmh: Float? = null,
    val ttcS: Float? = null,
    val headwayS: Float? = null,
    val driverState: String = "unknown",
    val driverAlertness: Float? = null,
    val longitudinalAccelMps2: Float? = null,
    val lateralAccelMps2: Float? = null,
    val activeEvents: List<String> = emptyList(),
    val tripId: String? = null,
    val vehicleId: String = BuildConfig.VEHICLE_ID,
    val connected: Boolean = false,
    val lastUpdatedMs: Long = 0L,
)

val TelemetryState.speedLabel: String get() =
    speedKmh?.let { "%.0f km/h".format(it) } ?: "-- km/h"

val TelemetryState.ttcLabel: String get() =
    ttcS?.let { "%.1f s".format(it) } ?: "--"

val TelemetryState.driverStateLabel: String get() = when (driverState) {
    "attentive" -> "ATTENTIVE"
    "distracted" -> "DISTRACTED"
    "drowsy" -> "DROWSY"
    else -> "UNKNOWN"
}

val TelemetryState.driverStateIsAlert: Boolean get() = driverState == "attentive"
val TelemetryState.driverStateIsWarning: Boolean get() = driverState == "distracted"
val TelemetryState.driverStateIsCritical: Boolean get() = driverState == "drowsy"

val TelemetryState.ttcRisk: Int get() = when {
    ttcS == null -> 0
    ttcS < 1.5f -> 5
    ttcS < 2.5f -> 4
    ttcS < 4.0f -> 3
    else -> 1
}

class TelemetryViewModel : ViewModel() {
    private val client = FleetIqApiClient(BuildConfig.FLEETIQ_API_URL)
    private val mutableState = MutableStateFlow(TelemetryState())
    val state: StateFlow<TelemetryState> = mutableState.asStateFlow()

    private var consecutiveFailures = 0

    init {
        viewModelScope.launch(Dispatchers.IO) {
            while (isActive) {
                val interval = backoffInterval(consecutiveFailures)
                delay(interval)
                val result = runCatching {
                    client.fetchLatestTelemetry(BuildConfig.VEHICLE_ID)
                }
                result.fold(
                    onSuccess = { telemetry ->
                        consecutiveFailures = 0
                        if (telemetry != null) mutableState.value = telemetry
                        else mutableState.value = mutableState.value.copy(connected = true)
                    },
                    onFailure = {
                        consecutiveFailures++
                        mutableState.value = mutableState.value.copy(connected = false)
                    },
                )
            }
        }
    }

    companion object {
        private const val BASE_INTERVAL_MS = 1_000L
        private const val MAX_INTERVAL_MS = 8_000L

        fun backoffInterval(failures: Int): Long =
            minOf(BASE_INTERVAL_MS * (1L shl minOf(failures, 3)), MAX_INTERVAL_MS)
    }
}

class FleetIqApiClient(private val baseUrl: String) {

    /** Fetch the latest telemetry point for a vehicle by resolving its active trip. */
    fun fetchLatestTelemetry(vehicleId: String): TelemetryState? {
        val tripId = resolveActiveTripId(vehicleId) ?: return null
        val trajectoryJson = get("/api/v1/trips/${tripId.encodeUrl()}/trajectory")
            ?: return TelemetryState(tripId = tripId, vehicleId = vehicleId, connected = true)

        val points = trajectoryJson.optJSONArray("points") ?: return null
        if (points.length() == 0) return TelemetryState(tripId = tripId, vehicleId = vehicleId, connected = true)

        val last = points.getJSONObject(points.length() - 1)
        val activeEvents = mutableListOf<String>()
        val eventsArr: JSONArray? = last.optJSONArray("active_event_types")
        if (eventsArr != null) {
            for (i in 0 until eventsArr.length()) activeEvents.add(eventsArr.getString(i))
        }

        return TelemetryState(
            speedKmh = last.optDouble("speed_kmh", Double.NaN)
                .takeIf { !it.isNaN() }?.toFloat(),
            ttcS = last.optDouble("min_ttc_s", Double.NaN)
                .takeIf { !it.isNaN() }?.toFloat(),
            headwayS = last.optDouble("headway_s", Double.NaN)
                .takeIf { !it.isNaN() }?.toFloat(),
            driverState = last.optString("driver_state", "unknown"),
            driverAlertness = last.optDouble("driver_alertness", Double.NaN)
                .takeIf { !it.isNaN() }?.toFloat(),
            longitudinalAccelMps2 = last.optDouble("longitudinal_accel_mps2", Double.NaN)
                .takeIf { !it.isNaN() }?.toFloat(),
            lateralAccelMps2 = last.optDouble("lateral_accel_mps2", Double.NaN)
                .takeIf { !it.isNaN() }?.toFloat(),
            activeEvents = activeEvents,
            tripId = tripId,
            vehicleId = vehicleId,
            connected = true,
            lastUpdatedMs = System.currentTimeMillis(),
        )
    }

    private fun resolveActiveTripId(vehicleId: String): String? {
        val tripsJson = get("/api/v1/trips") ?: return null
        val items = tripsJson.optJSONArray("items") ?: return null
        for (i in 0 until items.length()) {
            val item = items.getJSONObject(i)
            if (item.optString("vehicle_id") == vehicleId &&
                item.optString("status") in setOf("active", "processing")
            ) {
                return item.optString("trip_id").takeIf { it.isNotBlank() }
            }
        }
        // Fall back to first available trip with matching vehicle
        for (i in 0 until items.length()) {
            val item = items.getJSONObject(i)
            if (item.optString("vehicle_id") == vehicleId) {
                return item.optString("trip_id").takeIf { it.isNotBlank() }
            }
        }
        return null
    }

    private fun get(path: String): JSONObject? {
        val url = URL("${baseUrl.trimEnd('/')}$path")
        val conn = url.openConnection() as HttpURLConnection
        conn.requestMethod = "GET"
        conn.connectTimeout = 2_000
        conn.readTimeout = 2_000
        conn.setRequestProperty("Accept", "application/json")
        return try {
            val status = conn.responseCode
            if (status != 200) return null
            val body = conn.inputStream.bufferedReader().use { it.readText() }
            val envelope = JSONObject(body)
            envelope.optJSONObject("data")
        } finally {
            conn.disconnect()
        }
    }

    private fun String.encodeUrl(): String =
        java.net.URLEncoder.encode(this, Charsets.UTF_8.name())
}
