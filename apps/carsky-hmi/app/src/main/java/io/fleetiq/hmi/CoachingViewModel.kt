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
import org.json.JSONObject

data class CoachingCommand(
    val commandId: String,
    val severity: Int,
    val title: String,
    val message: String,
)

sealed interface CoachingState {
    val commandId: String?
    val severity: Int
    val title: String
    val message: String
    val connected: Boolean
    val acknowledged: Boolean
    val allowLongExplanation: Boolean

    data object Empty : CoachingState {
        override val commandId: String? = null
        override val severity: Int = 0
        override val title: String = "Monitoring"
        override val message: String = "No active coaching"
        override val connected: Boolean = false
        override val acknowledged: Boolean = false
        override val allowLongExplanation: Boolean = false
    }

    data class Idle(
        override val connected: Boolean,
    ) : CoachingState {
        override val commandId: String? = null
        override val severity: Int = 0
        override val title: String = "Monitoring"
        override val message: String = "No active coaching"
        override val acknowledged: Boolean = false
        override val allowLongExplanation: Boolean = false
    }

    data class Active(
        override val commandId: String,
        override val severity: Int,
        override val title: String,
        override val message: String,
        override val connected: Boolean = true,
        override val acknowledged: Boolean = false,
        override val allowLongExplanation: Boolean,
    ) : CoachingState
}

class CoachingViewModel : ViewModel() {
    private val client = CoachingBridgeClient(BuildConfig.CARSKY_BRIDGE_URL)
    private val mutableState = MutableStateFlow<CoachingState>(CoachingState.Empty)
    val state: StateFlow<CoachingState> = mutableState.asStateFlow()

    private var consecutiveFailures = 0

    init {
        viewModelScope.launch(Dispatchers.IO) {
            while (isActive) {
                val interval = pollInterval(consecutiveFailures)
                val result = runCatching { client.current(VEHICLE_ID) }
                mutableState.value = result.fold(
                    onSuccess = { command ->
                        consecutiveFailures = 0
                        connectionState(mutableState.value, connected = true, command)
                    },
                    onFailure = {
                        consecutiveFailures++
                        connectionState(mutableState.value, connected = false, command = null)
                    },
                )
                delay(interval)
            }
        }
    }

    fun acknowledge() {
        val next = acknowledge(mutableState.value)
        mutableState.value = next
        val commandId = next.commandId ?: return
        viewModelScope.launch(Dispatchers.IO) {
            runCatching { client.acknowledge(commandId) }
        }
    }

    companion object {
        val VEHICLE_ID: String get() = BuildConfig.VEHICLE_ID
        private const val POLL_INTERVAL_MS = 1_000L
        private const val MAX_INTERVAL_MS = 8_000L

        fun pollInterval(failures: Int): Long =
            minOf(POLL_INTERVAL_MS * (1L shl minOf(failures, 3)), MAX_INTERVAL_MS)

        fun reduce(previous: CoachingState, command: CoachingCommand): CoachingState {
            require(command.severity in 1..5) { "severity must be between 1 and 5" }
            require(command.commandId.isNotBlank()) { "commandId is required" }
            require(command.title.isNotBlank()) { "title is required" }
            require(command.message.isNotBlank()) { "message is required" }
            val wasAcknowledged =
                previous.commandId == command.commandId && previous.acknowledged
            return CoachingState.Active(
                commandId = command.commandId,
                severity = command.severity,
                title = command.title.take(48),
                message = command.message.take(120),
                acknowledged = wasAcknowledged,
                allowLongExplanation = command.severity < 4,
            )
        }

        fun acknowledge(state: CoachingState): CoachingState =
            if (state is CoachingState.Active) state.copy(acknowledged = true) else state

        fun connectionState(
            previous: CoachingState,
            connected: Boolean,
            command: CoachingCommand?,
        ): CoachingState {
            if (command != null) return reduce(previous, command)
            return if (!connected && previous is CoachingState.Active) {
                previous.copy(connected = false)
            } else {
                CoachingState.Idle(connected)
            }
        }
    }
}

class CoachingBridgeClient(private val baseUrl: String) {
    fun current(vehicleId: String): CoachingCommand? {
        val connection = open(
            "$baseUrl/v1/coaching/current?vehicle_id=${vehicleId.encodeUrlSegment()}",
            "GET",
        )
        return connection.useResponse { status, body ->
            if (status == HttpURLConnection.HTTP_NO_CONTENT) return@useResponse null
            check(status == HttpURLConnection.HTTP_OK) { "bridge unavailable" }
            val payload = JSONObject(body)
            CoachingCommand(
                commandId = payload.getString("command_id"),
                severity = payload.getInt("severity"),
                title = payload.getString("title"),
                message = payload.getString("message"),
            )
        }
    }

    fun acknowledge(commandId: String) {
        val connection = open(
            "$baseUrl/v1/coaching/${commandId.encodeUrlSegment()}/ack",
            "POST",
        )
        connection.useResponse { status, _ ->
            check(status == HttpURLConnection.HTTP_OK) { "acknowledgement failed" }
        }
    }

    private fun open(endpoint: String, method: String): HttpURLConnection =
        (URL(endpoint).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 1_500
            readTimeout = 1_500
            setRequestProperty("Accept", "application/json")
            if (method == "POST") doOutput = true
        }

    private fun <T> HttpURLConnection.useResponse(
        block: (status: Int, body: String) -> T,
    ): T = try {
        if (doOutput) outputStream.use { it.write(ByteArray(0)) }
        val status = responseCode
        val stream = if (status >= 400) errorStream else inputStream
        block(status, stream?.bufferedReader()?.use { it.readText() }.orEmpty())
    } finally {
        disconnect()
    }
}

private fun String.encodeUrlSegment(): String =
    java.net.URLEncoder.encode(this, Charsets.UTF_8.name())
