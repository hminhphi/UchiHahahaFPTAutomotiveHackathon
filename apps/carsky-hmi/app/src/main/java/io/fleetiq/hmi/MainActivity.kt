package io.fleetiq.hmi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val coachingViewModel: CoachingViewModel = viewModel()
            val state by coachingViewModel.state.collectAsStateWithLifecycle()
            FleetIqHmi(state = state, onAcknowledge = coachingViewModel::acknowledge)
        }
    }
}

@Composable
private fun FleetIqHmi(state: CoachingState, onAcknowledge: () -> Unit) {
    val severityColor = when (state.severity) {
        5 -> Color(0xFFD9362B)
        4 -> Color(0xFFE56E25)
        3 -> Color(0xFFF0B429)
        else -> Color(0xFF2A9D8F)
    }
    MaterialTheme {
        Surface(color = Color(0xFFF3F0E8), modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier.padding(horizontal = 56.dp, vertical = 36.dp),
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("FLEETIQ GUARDIAN", fontWeight = FontWeight.Black, fontSize = 24.sp)
                    Text(
                        if (state.connected) "CONNECTED" else "OFFLINE",
                        color = if (state.connected) Color(0xFF16796F) else Color(0xFF7A7167),
                        fontWeight = FontWeight.Bold,
                    )
                }

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color.White, RoundedCornerShape(24.dp))
                        .padding(40.dp),
                ) {
                    Column {
                        Text(
                            if (state.severity > 0) "RISK ${state.severity}/5" else "ROAD MONITOR",
                            color = severityColor,
                            fontWeight = FontWeight.Black,
                            fontSize = 20.sp,
                        )
                        Spacer(Modifier.height(18.dp))
                        Text(state.title, fontWeight = FontWeight.Black, fontSize = 42.sp)
                        Spacer(Modifier.height(10.dp))
                        Text(state.message, color = Color(0xFF34302B), fontSize = 30.sp)
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        acknowledgementLabel(state),
                        color = Color(0xFF5C554D),
                    )
                    Button(
                        enabled = state.commandId != null && !state.acknowledged,
                        onClick = onAcknowledge,
                        colors = ButtonDefaults.buttonColors(containerColor = severityColor),
                    ) {
                        Text("ACKNOWLEDGE", modifier = Modifier.padding(10.dp))
                    }
                }
            }
        }
    }
}

internal fun acknowledgementLabel(state: CoachingState): String = when {
    state.commandId == null -> "System ready"
    state.acknowledged -> "Driver acknowledged"
    else -> "Awaiting acknowledgement"
}
