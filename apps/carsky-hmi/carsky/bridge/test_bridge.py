import unittest
from datetime import UTC, datetime, timedelta

from bridge import CoachingStore, InvalidCommand, is_command_route


def command(
    *,
    command_id: str = "command-1",
    priority: int = 5,
    expires_at: datetime | None = None,
) -> dict[str, object]:
    expiry = expires_at or datetime.now(UTC) + timedelta(seconds=30)
    return {
        "schema_version": "1.0",
        "command_id": command_id,
        "event_id": "04eb7d40-cb01-469c-ac30-e2b06f66ae3a",
        "correlation_id": "correlation-1",
        "vehicle_id": "vehicle-1",
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": expiry.isoformat(),
        "channel": "visual",
        "priority": priority,
        "title": "Collision risk",
        "message": "Brake now. Increase distance.",
        "dedupe_key": f"dedupe-{command_id}",
    }


class CoachingStoreTest(unittest.TestCase):
    def test_deduplicates_commands_and_tracks_acknowledgement(self) -> None:
        store = CoachingStore()

        first = store.accept(command())
        duplicate = store.accept(command())
        acknowledged = store.acknowledge("command-1")

        self.assertEqual(first.command_id, duplicate.command_id)
        self.assertEqual(1, store.command_count)
        self.assertTrue(acknowledged.acknowledged)

    def test_rejects_out_of_range_priority(self) -> None:
        store = CoachingStore()

        with self.assertRaises(InvalidCommand):
            store.accept(command(priority=6))

    def test_expired_command_is_not_returned_to_the_driver(self) -> None:
        store = CoachingStore()
        store.accept(command(expires_at=datetime.now(UTC) - timedelta(seconds=1)))

        self.assertIsNone(store.current("vehicle-1"))

    def test_accepts_the_canonical_carsky_node_command_route(self) -> None:
        self.assertTrue(is_command_route("/api/rooms/room-1/nodes/node-1/commands"))
        self.assertFalse(is_command_route("/api/rooms/../nodes/node-1/commands"))


if __name__ == "__main__":
    unittest.main()
