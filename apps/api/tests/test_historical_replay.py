import asyncio

from fleetiq_api.historical_replay import FilesystemTripMediaStore, HistoricalTripFrameReader


def test_filesystem_store_discovers_organizer_road_and_driver_frames(tmp_path) -> None:
    road = tmp_path / "T01-Sample" / "kitti" / "image_2"
    driver = tmp_path / "T01-Sample" / "driver"
    road.mkdir(parents=True)
    driver.mkdir(parents=True)
    (road / "000005.jpg").write_bytes(b"road")
    (road / "000002.jpg").write_bytes(b"road")
    (driver / "frame_000003.jpg").write_bytes(b"driver")

    async def scenario() -> tuple[tuple[str, ...], list[int], list[int]]:
        store = FilesystemTripMediaStore(tmp_path)
        trips = await store.list_trip_ids()
        road_frames = await store.list_frames("T01-Sample", "road_left")
        driver_frames = await store.list_frames("T01-Sample", "driver")
        return trips, [frame.frame_index for frame in road_frames], [frame.frame_index for frame in driver_frames]

    trips, road_frames, driver_frames = asyncio.run(scenario())

    assert trips == ("T01-Sample",)
    assert road_frames == [2, 5]
    assert driver_frames == [3]


def test_historical_frame_reader_returns_one_exact_frame(tmp_path) -> None:
    road = tmp_path / "T01-Sample" / "kitti" / "image_2"
    road.mkdir(parents=True)
    # A minimal JPEG containing only the SOF dimensions needed by the API reader.
    jpeg = b"\xff\xd8\xff\xc0\x00\x11\x08\x00\x02\x00\x03" + (b"\x00" * 10) + b"\xff\xd9"
    (road / "000012.jpg").write_bytes(jpeg)

    async def scenario():
        return await HistoricalTripFrameReader(FilesystemTripMediaStore(tmp_path)).get_frame(
            "T01-Sample", "road_left", 12
        )

    frame = asyncio.run(scenario())

    assert frame.metadata.frame_index == 12
    assert (frame.metadata.width, frame.metadata.height) == (3, 2)
    assert frame.jpeg == jpeg
