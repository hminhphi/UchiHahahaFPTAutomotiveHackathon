package io.fleetiq.hmi

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CoachingViewModelTest {
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
}
