package io.fleetiq.hmi

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CoachingViewModelTest {

    // ── existing tests (unchanged) ───────────────────────────────────────────

    @Test
    fun criticalCommandUsesShortSafetyCopy() {
        val state = CoachingViewModel.reduce(
            CoachingState.Empty,
            CoachingCommand(
                commandId = "command-1",
                severity = 5,
                title = "Brake",
                message = "Brake now",
            ),
        )
        assertEquals("Brake now", state.message)
        assertFalse(state.allowLongExplanation)
    }

    @Test
    fun acknowledgementKeepsTheActiveCommandIdentity() {
        val active = CoachingViewModel.reduce(
            CoachingState.Empty,
            CoachingCommand(
                commandId = "command-2",
                severity = 4,
                title = "High risk",
                message = "Increase following distance",
            ),
        )
        val acknowledged = CoachingViewModel.acknowledge(active)
        assertEquals("command-2", acknowledged.commandId)
        assertTrue(acknowledged.acknowledged)
    }

    @Test
    fun connectedBridgeWithoutCommandShowsConnectedIdle() {
        val state = CoachingViewModel.connectionState(
            previous = CoachingState.Empty,
            connected = true,
            command = null,
        )
        assertTrue(state.connected)
        assertEquals("No active coaching", state.message)
    }

    @Test
    fun idleStateDoesNotAskForAcknowledgement() {
        assertEquals("System ready", acknowledgementLabel(CoachingState.Idle(connected = true)))
    }

    // ── new tests ────────────────────────────────────────────────────────────

    @Test
    fun titleIsTruncatedAt48Chars() {
        val longTitle = "A".repeat(60)
        val state = CoachingViewModel.reduce(
            CoachingState.Empty,
            CoachingCommand("cmd-3", severity = 3, title = longTitle, message = "msg"),
        )
        assertEquals(48, state.title.length)
    }

    @Test
    fun messageIsTruncatedAt120Chars() {
        val longMsg = "B".repeat(150)
        val state = CoachingViewModel.reduce(
            CoachingState.Empty,
            CoachingCommand("cmd-4", severity = 2, title = "T", message = longMsg),
        )
        assertEquals(120, state.message.length)
    }

    @Test
    fun severity1and2AllowLongExplanation() {
        for (sev in 1..3) {
            val state = CoachingViewModel.reduce(
                CoachingState.Empty,
                CoachingCommand("cmd-$sev", severity = sev, title = "T", message = "M"),
            )
            assertTrue("severity $sev should allow long explanation", state.allowLongExplanation)
        }
    }

    @Test
    fun severity4and5DisableLongExplanation() {
        for (sev in 4..5) {
            val state = CoachingViewModel.reduce(
                CoachingState.Empty,
                CoachingCommand("cmd-$sev", severity = sev, title = "T", message = "M"),
            )
            assertFalse("severity $sev should disable long explanation", state.allowLongExplanation)
        }
    }

    @Test
    fun sameCommandIdKeepsAcknowledgedFlag() {
        val first = CoachingViewModel.reduce(
            CoachingState.Empty,
            CoachingCommand("cmd-dup", severity = 3, title = "T", message = "M"),
        )
        val acked = CoachingViewModel.acknowledge(first)
        // Re-reduce with same command id → still acknowledged
        val second = CoachingViewModel.reduce(
            acked,
            CoachingCommand("cmd-dup", severity = 3, title = "T", message = "M"),
        )
        assertTrue(second.acknowledged)
    }

    @Test
    fun differentCommandIdClearsAcknowledgedFlag() {
        val first = CoachingViewModel.reduce(
            CoachingState.Empty,
            CoachingCommand("cmd-a", severity = 3, title = "T", message = "M"),
        )
        val acked = CoachingViewModel.acknowledge(first)
        val second = CoachingViewModel.reduce(
            acked,
            CoachingCommand("cmd-b", severity = 3, title = "T", message = "M"),
        )
        assertFalse(second.acknowledged)
    }

    @Test
    fun offlineTransitionPreservesActiveCommandWithConnectedFalse() {
        val active = CoachingViewModel.reduce(
            CoachingState.Empty,
            CoachingCommand("cmd-x", severity = 4, title = "T", message = "M"),
        )
        val offline = CoachingViewModel.connectionState(
            previous = active,
            connected = false,
            command = null,
        )
        // Title/message preserved, connected false
        assertEquals("T", offline.title)
        assertFalse(offline.connected)
    }

    @Test
    fun pollIntervalDoublesWithEachFailureUpToCap() {
        assertEquals(1_000L, CoachingViewModel.pollInterval(0))
        assertEquals(2_000L, CoachingViewModel.pollInterval(1))
        assertEquals(4_000L, CoachingViewModel.pollInterval(2))
        assertEquals(8_000L, CoachingViewModel.pollInterval(3))
        assertEquals(8_000L, CoachingViewModel.pollInterval(10)) // capped
    }

    @Test
    fun acknowledgeOnIdleStateIsNoOp() {
        val idle = CoachingState.Idle(connected = true)
        val result = CoachingViewModel.acknowledge(idle)
        assertNull(result.commandId)
        assertFalse(result.acknowledged)
    }

    @Test
    fun acknowledgeOnEmptyStateIsNoOp() {
        val result = CoachingViewModel.acknowledge(CoachingState.Empty)
        assertNull(result.commandId)
    }
}

class TelemetryStateTest {

    @Test
    fun speedLabelFormatsKmh() {
        val t = TelemetryState(speedKmh = 72.3f)
        assertEquals("72 km/h", t.speedLabel)
    }

    @Test
    fun speedLabelIsDashWhenNull() {
        assertEquals("-- km/h", TelemetryState().speedLabel)
    }

    @Test
    fun ttcLabelFormatsOneDecimal() {
        val t = TelemetryState(ttcS = 3.14f)
        assertEquals("3.1 s", t.ttcLabel)
    }

    @Test
    fun ttcRiskIsCriticalBelow1s5() {
        assertEquals(5, TelemetryState(ttcS = 1.0f).ttcRisk)
    }

    @Test
    fun ttcRiskIsHighBetween1s5and2s5() {
        assertEquals(4, TelemetryState(ttcS = 2.0f).ttcRisk)
    }

    @Test
    fun ttcRiskIsLowAbove4s() {
        assertEquals(1, TelemetryState(ttcS = 5.0f).ttcRisk)
    }

    @Test
    fun ttcRiskIsZeroWhenNull() {
        assertEquals(0, TelemetryState(ttcS = null).ttcRisk)
    }

    @Test
    fun driverStateLabelsAreUppercase() {
        assertEquals("ATTENTIVE", TelemetryState(driverState = "attentive").driverStateLabel)
        assertEquals("DISTRACTED", TelemetryState(driverState = "distracted").driverStateLabel)
        assertEquals("DROWSY", TelemetryState(driverState = "drowsy").driverStateLabel)
        assertEquals("UNKNOWN", TelemetryState(driverState = "unknown").driverStateLabel)
    }

    @Test
    fun driverStateAlertFlagsAreExclusive() {
        val attentive = TelemetryState(driverState = "attentive")
        assertTrue(attentive.driverStateIsAlert)
        assertFalse(attentive.driverStateIsWarning)
        assertFalse(attentive.driverStateIsCritical)

        val drowsy = TelemetryState(driverState = "drowsy")
        assertFalse(drowsy.driverStateIsAlert)
        assertTrue(drowsy.driverStateIsCritical)
    }

    @Test
    fun backoffIntervalCapsBeyondThreeFailures() {
        assertEquals(TelemetryViewModel.backoffInterval(3), TelemetryViewModel.backoffInterval(99))
    }
}
