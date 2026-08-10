"""Idempotent historical logistics import tests."""

import pytest

from fleetiq_api.dependencies import InMemoryOperationsRepository
from fleetiq_api.historical_import import HistoricalTripImporter


class FakeMedia:
    async def list_trip_ids(self) -> tuple[str, ...]:
        return ("T01-Sample",)

    async def read_trip_document(self, trip_id: str) -> dict[str, object]:
        return {
            "trip_id": trip_id,
            "frames": [
                {
                    "frame_id": 3,
                    "timestamp": 0.15,
                    "ego": {
                        "speed_kmh": 42.0,
                        "longitudinal_accel": -182.161,
                        "lateral_accel": 0.2,
                    },
                }
            ],
        }


@pytest.mark.anyio
async def test_importer_is_idempotent_and_assigns_mock_logistics() -> None:
    repository = InMemoryOperationsRepository()
    importer = HistoricalTripImporter(
        FakeMedia(),
        repository,
        {
            "T01-Sample": {
                "vehicle_id": "VH-01", "vehicle_class": "delivery_van", "license_plate": "51D-10001",
                "length_m": 5.4, "width_m": 2.0, "height_m": 2.4, "payload_capacity_kg": 1200,
                "depot_name": "District 1 Hub", "driver_id": "DRV-01", "driver_name": "Minh Tran",
                "employee_code": "FLEET-001", "license_class": "B2", "route_name": "Central retail loop",
                "cargo_class": "parcel", "order_count": 12,
            }
        },
        seed_version="logistics-v1",
    )

    first = await importer.import_trip("T01-Sample")
    second = await importer.import_trip("T01-Sample")
    all_results = await importer.import_all()

    trip = await repository.get_trip("T01-Sample")
    assert first.status == "imported"
    assert second.status == "unchanged"
    assert [result.trip_id for result in all_results] == ["T01-Sample"]
    assert trip is not None and trip.order_count == 12
    assert trip.vehicle_class == "delivery_van"
    assert len(repository.trips_by_id) == 1
    assert len(repository.telemetry_by_trip["T01-Sample"]) == 1
    assert repository.telemetry_by_trip["T01-Sample"][3].longitudinal_accel_mps2 == -182.161
