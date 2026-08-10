package io.fleetiq.hmi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

// ── Colour palette ──────────────────────────────────────────────────────────
private val BgSurface   = Color(0xFF0B0F1A)
private val BgCard      = Color(0xFF111827)
private val BgCardBdr   = Color(0xFF1F2937)
private val TextPrimary = Color(0xFFF3F4F6)
private val TextMuted   = Color(0xFF9CA3AF)
private val AccentBlue  = Color(0xFF3B82F6)
private val SevCritical = Color(0xFFEF4444)
private val SevHigh     = Color(0xFFF97316)
private val SevMed      = Color(0xFFF59E0B)
private val SevLow      = Color(0xFF22C55E)
private val DmsAlert    = Color(0xFFEC4899)

fun severityColor(sev: Int): Color = when (sev) {
    5    -> SevCritical
    4    -> SevHigh
    3    -> SevMed
    else -> SevLow
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val coachingVm: CoachingViewModel = viewModel()
            val telemetryVm: TelemetryViewModel = viewModel()
            val coaching by coachingVm.state.collectAsStateWithLifecycle()
            val telemetry by telemetryVm.state.collectAsStateWithLifecycle()

            MaterialTheme(colorScheme = darkColorScheme()) {
                FleetIqHmi(
                    coaching  = coaching,
                    telemetry = telemetry,
                    onAcknowledge = coachingVm::acknowledge,
                )
            }
        }
    }
}

@Composable
fun FleetIqHmi(
    coaching: CoachingState,
    telemetry: TelemetryState,
    onAcknowledge: () -> Unit,
) {
    Surface(color = BgSurface, modifier = Modifier.fillMaxSize()) {
        // Landscape 3-column layout:
        // [Telemetry strip | Coaching card | DMS + ack footer]
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // ── Left column: live telemetry ──────────────────────────────
            Column(
                modifier = Modifier
                    .width(220.dp)
                    .fillMaxHeight(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                HmiHeader(coaching.connected || telemetry.connected, telemetry.vehicleId)
                Spacer(Modifier.height(4.dp))
                TelemetryCard(telemetry)
            }

            // ── Centre column: coaching alert card ───────────────────────
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
                contentAlignment = Alignment.Center,
            ) {
                CoachingCard(coaching)
            }

            // ── Right column: DMS indicator + ack button ─────────────────
            Column(
                modifier = Modifier
                    .width(210.dp)
                    .fillMaxHeight(),
                verticalArrangement = Arrangement.SpaceBetween,
                horizontalAlignment = Alignment.End,
            ) {
                DmsPanel(telemetry)
                AckPanel(coaching, onAcknowledge)
            }
        }
    }
}

// ── Header ───────────────────────────────────────────────────────────────────
@Composable
private fun HmiHeader(connected: Boolean, vehicleId: String) {
    Column {
        Text(
            "FLEETIQ GUARDIAN",
            color = TextPrimary,
            fontWeight = FontWeight.Black,
            fontSize = 15.sp,
            letterSpacing = 2.sp,
        )
        Text(
            vehicleId,
            color = TextMuted,
            fontSize = 11.sp,
        )
        Spacer(Modifier.height(6.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            val dotColor = if (connected) SevLow else TextMuted
            Box(
                Modifier
                    .width(8.dp)
                    .height(8.dp)
                    .background(dotColor, RoundedCornerShape(4.dp)),
            )
            Spacer(Modifier.width(6.dp))
            Text(
                if (connected) "CONNECTED" else "OFFLINE",
                color = dotColor,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp,
            )
        }
    }
}

// ── Live telemetry card ───────────────────────────────────────────────────────
@Composable
private fun TelemetryCard(t: TelemetryState) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(BgCard, RoundedCornerShape(14.dp))
            .border(1.dp, BgCardBdr, RoundedCornerShape(14.dp))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        MetricRow(label = "SPEED", value = t.speedLabel, highlight = false)
        MetricRow(
            label = "TTC",
            value = t.ttcLabel + " s",
            highlight = t.ttcS != null && t.ttcS < 2.5f,
            highlightColor = if (t.ttcS != null && t.ttcS < 1.5f) SevCritical else SevHigh,
        )
        MetricRow(
            label = "HEADWAY",
            value = t.headwayS?.let { "%.1f s".format(it) } ?: "--",
            highlight = false,
        )
        if (t.longitudinalAccelMps2 != null) {
            MetricRow(
                label = "LONG ACCEL",
                value = "%.1f m/s²".format(t.longitudinalAccelMps2),
                highlight = t.longitudinalAccelMps2 < -3f,
                highlightColor = SevHigh,
            )
        }
        if (t.tripId != null) {
            Spacer(Modifier.height(0.dp))
            Text(t.tripId, color = TextMuted, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        // Active event chips
        if (t.activeEvents.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                t.activeEvents.take(3).forEach { ev ->
                    Text(
                        ev.replace('_', ' ').uppercase(),
                        color = SevHigh,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier
                            .background(SevHigh.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 5.dp, vertical = 2.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun MetricRow(
    label: String,
    value: String,
    highlight: Boolean,
    highlightColor: Color = SevHigh,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = TextMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
        Text(
            value,
            color = if (highlight) highlightColor else TextPrimary,
            fontWeight = if (highlight) FontWeight.Black else FontWeight.Bold,
            fontSize = 16.sp,
        )
    }
}

// ── Coaching alert card ───────────────────────────────────────────────────────
@Composable
private fun CoachingCard(coaching: CoachingState) {
    val sev = coaching.severity
    val accentColor by animateColorAsState(
        targetValue = severityColor(sev),
        animationSpec = tween(400),
        label = "severity-color",
    )

    // Pulse alpha for critical unacknowledged alerts
    val pulseAlpha = if (sev >= 4 && !coaching.acknowledged && coaching.commandId != null) {
        val inf = rememberInfiniteTransition(label = "pulse")
        val a by inf.animateFloat(
            initialValue = 0.7f,
            targetValue = 1.0f,
            animationSpec = infiniteRepeatable(tween(600), RepeatMode.Reverse),
            label = "pulse-alpha",
        )
        a
    } else 1f

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(BgCard, RoundedCornerShape(20.dp))
            .border(2.dp, accentColor.copy(alpha = 0.5f * pulseAlpha), RoundedCornerShape(20.dp))
            .padding(32.dp)
            .alpha(pulseAlpha),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Severity badge
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            if (sev > 0) {
                Box(
                    modifier = Modifier
                        .background(accentColor, RoundedCornerShape(8.dp))
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                ) {
                    Text(
                        "RISK $sev/5",
                        color = Color.White,
                        fontWeight = FontWeight.Black,
                        fontSize = 13.sp,
                        letterSpacing = 1.sp,
                    )
                }
            } else {
                Text(
                    "ROAD MONITOR",
                    color = TextMuted,
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp,
                    letterSpacing = 1.sp,
                )
            }
            if (coaching.acknowledged) {
                Text(
                    "✓ ACK",
                    color = SevLow,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp,
                )
            }
        }

        // Title
        Text(
            coaching.title,
            color = TextPrimary,
            fontWeight = FontWeight.Black,
            fontSize = 38.sp,
            lineHeight = 42.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )

        // Message
        if (coaching.allowLongExplanation || coaching.severity == 0) {
            Text(
                coaching.message,
                color = TextMuted,
                fontSize = 22.sp,
                lineHeight = 28.sp,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
        } else {
            // Critical — short phrase only, large
            Text(
                coaching.message,
                color = accentColor,
                fontWeight = FontWeight.Bold,
                fontSize = 26.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

// ── DMS panel ────────────────────────────────────────────────────────────────
@Composable
private fun DmsPanel(t: TelemetryState) {
    val dmsColor = when {
        t.driverStateIsCritical -> DmsAlert
        t.driverStateIsWarning  -> SevHigh
        t.driverStateIsAlert    -> SevLow
        else                    -> TextMuted
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(BgCard, RoundedCornerShape(14.dp))
            .border(1.dp, BgCardBdr, RoundedCornerShape(14.dp))
            .padding(16.dp),
        horizontalAlignment = Alignment.End,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("DRIVER STATE", color = TextMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
        Text(
            t.driverStateLabel,
            color = dmsColor,
            fontWeight = FontWeight.Black,
            fontSize = 20.sp,
            letterSpacing = 1.sp,
        )
        t.driverAlertness?.let { alertness ->
            val pct = (alertness * 100).toInt()
            Text("${pct}% alertness", color = TextMuted, fontSize = 11.sp)
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .background(BgCardBdr, RoundedCornerShape(3.dp)),
            ) {
                Box(
                    Modifier
                        .fillMaxWidth(alertness.coerceIn(0f, 1f))
                        .fillMaxHeight()
                        .background(dmsColor, RoundedCornerShape(3.dp)),
                )
            }
        }
        if (t.ttcRisk >= 4) {
            Spacer(Modifier.height(2.dp))
            Text(
                "⚠ SHORT TTC",
                color = severityColor(t.ttcRisk),
                fontWeight = FontWeight.Bold,
                fontSize = 12.sp,
            )
        }
    }
}

// ── Acknowledgement panel ─────────────────────────────────────────────────────
@Composable
private fun AckPanel(coaching: CoachingState, onAcknowledge: () -> Unit) {
    val canAck = coaching.commandId != null && !coaching.acknowledged
    Column(
        horizontalAlignment = Alignment.End,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            acknowledgementLabel(coaching),
            color = TextMuted,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
        )
        Button(
            enabled = canAck,
            onClick = onAcknowledge,
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = severityColor(coaching.severity),
                disabledContainerColor = BgCard,
            ),
            modifier = Modifier.height(52.dp),
        ) {
            Text(
                "ACKNOWLEDGE",
                fontWeight = FontWeight.Black,
                fontSize = 14.sp,
                letterSpacing = 1.sp,
                modifier = Modifier.padding(horizontal = 8.dp),
            )
        }
    }
}

internal fun acknowledgementLabel(state: CoachingState): String = when {
    state.commandId == null -> "System ready"
    state.acknowledged      -> "Driver acknowledged"
    else                    -> "Awaiting acknowledgement"
}
