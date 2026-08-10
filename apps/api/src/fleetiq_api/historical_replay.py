"""Historical camera replay backed by local files or any S3-compatible object store."""

from __future__ import annotations

import asyncio
import csv
import gzip
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .config import ApiSettings
from .dependencies import CameraFrameSink, TripFrameReader, TripRepository, TripTrajectoryRepository
from .schemas import TrajectoryData, TripSummary
from .trajectory import build_trajectory
from .trip_summary import build_trip_summary
from .ws.frame_protocol import CameraFrame, CameraFrameMetadata


VIEW_DIRECTORIES = {"road_left": "image_2", "road_right": "image_3", "driver": "driver"}


@dataclass(frozen=True)
class StoredFrame:
    frame_index: int
    location: str


class TripMediaStore(Protocol):
    async def list_trip_ids(self) -> tuple[str, ...]: ...

    async def list_frames(self, trip_id: str, view: str) -> tuple[StoredFrame, ...]: ...

    async def read(self, frame: StoredFrame) -> bytes: ...

    async def read_trip_document(self, trip_id: str) -> dict[str, object]: ...


class FilesystemTripMediaStore:
    def __init__(self, root: Path, prediction_root: Path | None = None) -> None:
        self._root = root
        self._prediction_root = prediction_root

    async def list_trip_ids(self) -> tuple[str, ...]:
        return await asyncio.to_thread(self._list_trip_ids)

    def _list_trip_ids(self) -> tuple[str, ...]:
        if not self._root.is_dir():
            return ()
        return tuple(sorted(path.name for path in self._root.iterdir() if path.is_dir()))

    async def list_frames(self, trip_id: str, view: str) -> tuple[StoredFrame, ...]:
        return await asyncio.to_thread(self._list_frames, trip_id, view)

    def _list_frames(self, trip_id: str, view: str) -> tuple[StoredFrame, ...]:
        directory_name = VIEW_DIRECTORIES.get(view)
        if directory_name is None:
            return ()
        directory = (
            self._root / trip_id / directory_name
            if view == "driver"
            else self._root / trip_id / "kitti" / directory_name
        )
        if not directory.is_dir():
            return ()
        frames = []
        for path in directory.glob("*.jpg"):
            frame_index = _frame_index(path.stem)
            if frame_index is not None:
                frames.append(StoredFrame(frame_index=frame_index, location=str(path)))
        return tuple(sorted(frames, key=lambda frame: frame.frame_index))

    async def read(self, frame: StoredFrame) -> bytes:
        return await asyncio.to_thread(Path(frame.location).read_bytes)

    async def read_trip_document(self, trip_id: str) -> dict[str, object]:
        path = self._root / trip_id / f"{trip_id}.json.gz"
        document = await asyncio.to_thread(_read_trip_document, path.read_bytes())
        if self._prediction_root is None:
            return document
        prediction_path = self._prediction_root / f"{trip_id}_twostage.csv"
        return await asyncio.to_thread(
            _overlay_phone_predictions,
            document,
            prediction_path,
        )


class S3TripMediaStore:
    """MinIO and AWS S3 adapter. Object keys are kept independent of the vendor."""

    def __init__(self, settings: ApiSettings) -> None:
        self._bucket = settings.object_storage_bucket
        self._endpoint = urlsplit(settings.object_storage_endpoint or "")
        self._access_key = settings.object_storage_access_key or ""
        self._secret_key = settings.object_storage_secret_key or ""

    async def list_trip_ids(self) -> tuple[str, ...]:
        return await asyncio.to_thread(self._list_trip_ids)

    def _list_trip_ids(self) -> tuple[str, ...]:
        root = self._list(prefix="trips/", delimiter="/")
        return tuple(
            sorted(
                prefix.text.strip("/").split("/")[-1]
                for prefix in root.findall(".//{*}CommonPrefixes/{*}Prefix")
                if prefix.text and not prefix.text.strip("/").endswith("-Sample")
            )
        )

    async def list_frames(self, trip_id: str, view: str) -> tuple[StoredFrame, ...]:
        return await asyncio.to_thread(self._list_frames, trip_id, view)

    def _list_frames(self, trip_id: str, view: str) -> tuple[StoredFrame, ...]:
        directory_name = VIEW_DIRECTORIES.get(view)
        if directory_name is None:
            return ()
        root = "driver" if view == "driver" else f"kitti/{directory_name}"
        prefix = f"trips/{trip_id}/{root}/"
        document = self._list(prefix=prefix)
        frames: list[StoredFrame] = []
        for item in document.findall(".//{*}Contents"):
            key = item.findtext("{*}Key")
            if not key or not key.endswith(".jpg"):
                continue
            frame_index = _frame_index(Path(key).stem)
            if frame_index is not None:
                frames.append(StoredFrame(frame_index=frame_index, location=key))
        return tuple(sorted(frames, key=lambda frame: frame.frame_index))

    async def read(self, frame: StoredFrame) -> bytes:
        return await asyncio.to_thread(self._read, frame.location)

    async def read_trip_document(self, trip_id: str) -> dict[str, object]:
        contents = await asyncio.to_thread(self._read, f"trips/{trip_id}/{trip_id}.json.gz")
        return _read_trip_document(contents)

    def _read(self, key: str) -> bytes:
        return self._request("GET", key=key)

    def _list(self, *, prefix: str, delimiter: str | None = None) -> ElementTree.Element:
        query = {"list-type": "2", "prefix": prefix}
        if delimiter is not None:
            query["delimiter"] = delimiter
        return ElementTree.fromstring(self._request("GET", query=query))

    def _request(
        self,
        method: str,
        *,
        key: str = "",
        query: dict[str, str] | None = None,
    ) -> bytes:
        """Issue a path-style, AWS Signature V4 request accepted by MinIO and S3."""
        now = datetime.now(UTC)
        date_stamp = now.strftime("%Y%m%d")
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        canonical_uri = quote(
            f"{self._endpoint.path.rstrip('/')}/{self._bucket}/{key}".replace("//", "/"),
            safe="/-_.~",
        )
        canonical_query = "&".join(
            f"{quote(name, safe='-_.~')}={quote(value, safe='-_.~')}"
            for name, value in sorted((query or {}).items())
        )
        payload_hash = hashlib.sha256(b"").hexdigest()
        canonical_headers = (
            f"host:{self._endpoint.netloc}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        scope = f"{date_stamp}/us-east-1/s3/aws4_request"
        canonical_request = "\n".join(
            (method, canonical_uri, canonical_query, canonical_headers, signed_headers, payload_hash)
        )
        string_to_sign = "\n".join(
            ("AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest())
        )
        signing_key = _signing_key(self._secret_key, date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        authorization = (
            f"AWS4-HMAC-SHA256 Credential={self._access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        url = f"{self._endpoint.scheme}://{self._endpoint.netloc}{canonical_uri}"
        if canonical_query:
            url = f"{url}?{canonical_query}"
        request = Request(
            url,
            method=method,
            headers={
                "Authorization": authorization,
                "x-amz-content-sha256": payload_hash,
                "x-amz-date": amz_date,
            },
        )
        with urlopen(request, timeout=5) as response:  # noqa: S310 - endpoint is validated configuration
            return response.read()


class HistoricalTripRepository:
    def __init__(self, media: TripMediaStore) -> None:
        self._media = media

    async def list_trips(self) -> tuple[TripSummary, ...]:
        trip_ids = await self._media.list_trip_ids()
        results = await asyncio.gather(
            *(self._media.read_trip_document(trip_id) for trip_id in trip_ids),
            return_exceptions=True,
        )
        summaries: list[TripSummary] = []
        for trip_id, result in zip(trip_ids, results):
            if isinstance(result, BaseException):
                continue
            summaries.append(build_trip_summary(trip_id, result))
        return tuple(summaries)

    async def get_trajectory(self, trip_id: str) -> TrajectoryData:
        return build_trajectory(trip_id, await self._media.read_trip_document(trip_id))


class HistoricalTripFrameReader:
    """Random-access reader used by the browser timeline and evidence trace."""

    def __init__(self, media: TripMediaStore) -> None:
        self._media = media

    async def get_frame(self, trip_id: str, view: str, frame_index: int) -> CameraFrame:
        frames = await self._media.list_frames(trip_id, view)
        stored = next((frame for frame in frames if frame.frame_index == frame_index), None)
        if stored is None:
            raise FileNotFoundError(f"frame {frame_index} is unavailable for {trip_id}/{view}")
        jpeg = await self._media.read(stored)
        width, height = _jpeg_dimensions(jpeg)
        return CameraFrame(
            metadata=CameraFrameMetadata(
                schema_version="1.0",
                frame_index=stored.frame_index,
                occurred_at=datetime.now(UTC),
                width=width,
                height=height,
                correlation_id=f"frame.{trip_id}.{view}.{stored.frame_index:06d}",
            ),
            jpeg=jpeg,
        )


class HistoricalCameraReplay:
    def __init__(self, media: TripMediaStore, *, fps: float, loop: bool) -> None:
        self._media = media
        self._fps = fps
        self._loop = loop
        self._lock = asyncio.Lock()
        self._tasks: dict[tuple[str, str], asyncio.Task[None]] = {}
        self._leases: dict[tuple[str, str], int] = {}

    async def acquire(
        self,
        trip_id: str,
        view: str,
        sink: CameraFrameSink,
    ) -> "HistoricalReplayLease":
        key = (trip_id, view)
        async with self._lock:
            self._leases[key] = self._leases.get(key, 0) + 1
            task = self._tasks.get(key)
            if task is None or task.done():
                self._tasks[key] = asyncio.create_task(self._run(key, sink))
        return HistoricalReplayLease(self, key)

    async def release(self, key: tuple[str, str]) -> None:
        async with self._lock:
            remaining = self._leases.get(key, 0) - 1
            if remaining > 0:
                self._leases[key] = remaining
                return
            self._leases.pop(key, None)
            task = self._tasks.pop(key, None)
            if task is not None:
                task.cancel()

    async def _run(self, key: tuple[str, str], sink: CameraFrameSink) -> None:
        trip_id, view = key
        try:
            while True:
                frames = await self._media.list_frames(trip_id, view)
                if not frames:
                    return
                for frame in frames:
                    jpeg = await self._media.read(frame)
                    width, height = _jpeg_dimensions(jpeg)
                    payload = CameraFrame(
                        metadata=CameraFrameMetadata(
                            schema_version="1.0",
                            frame_index=frame.frame_index,
                            occurred_at=datetime.now(UTC),
                            width=width,
                            height=height,
                            correlation_id=f"replay.{trip_id}.{view}.{frame.frame_index:06d}",
                        ),
                        jpeg=jpeg,
                    )
                    await sink.publish(trip_id, view, payload)
                    await asyncio.sleep(1 / self._fps)
                if not self._loop:
                    return
                await asyncio.sleep(0.75)
        except asyncio.CancelledError:
            raise


class HistoricalReplayLease:
    def __init__(self, replay: HistoricalCameraReplay, key: tuple[str, str]) -> None:
        self._replay = replay
        self._key = key
        self._closed = False

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._replay.release(self._key)


def create_historical_dependencies(
    settings: ApiSettings,
) -> tuple[TripRepository, HistoricalCameraReplay, TripTrajectoryRepository, TripFrameReader]:
    media: TripMediaStore
    if settings.media_backend == "s3":
        media = S3TripMediaStore(settings)
    else:
        media = FilesystemTripMediaStore(
            settings.dataset_root,
            settings.dms_prediction_root,
        )
    trips = HistoricalTripRepository(media)
    return (
        trips,
        HistoricalCameraReplay(media, fps=settings.replay_fps, loop=settings.replay_loop),
        trips,
        HistoricalTripFrameReader(media),
    )


def _frame_index(stem: str) -> int | None:
    digits = "".join(character for character in stem if character.isdigit())
    return int(digits) if digits else None


def _read_trip_document(contents: bytes) -> dict[str, object]:
    import json

    loaded = json.loads(gzip.decompress(contents).decode("utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _overlay_phone_predictions(
    document: dict[str, object],
    path: Path,
) -> dict[str, object]:
    frames = document.get("frames")
    if not path.is_file() or not isinstance(frames, list):
        return document
    predictions: dict[int, bool] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            frame_value = row.get("frame_id", "")
            phone_value = row.get("phone_use", "").strip().casefold()
            if not frame_value.isdigit() or phone_value not in {"true", "false"}:
                continue
            predictions[int(frame_value)] = phone_value == "true"

    for frame in frames:
        if not isinstance(frame, dict) or frame.get("frame_id") not in predictions:
            continue
        driver = frame.setdefault("driver", {})
        if isinstance(driver, dict):
            driver["phone_use"] = predictions[frame["frame_id"]]
    return document


def _signing_key(secret: str, date_stamp: str) -> bytes:
    date_key = hmac.new(f"AWS4{secret}".encode(), date_stamp.encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, b"us-east-1", hashlib.sha256).digest()
    service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Read JPEG dimensions without bringing image tooling into the API container."""
    if len(data) < 10 or not data.startswith(b"\xff\xd8"):
        raise ValueError("replay object is not a JPEG")
    position = 2
    while position + 9 < len(data):
        if data[position] != 0xFF:
            position += 1
            continue
        marker = data[position + 1]
        position += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = int.from_bytes(data[position : position + 2], "big")
        if length < 2 or position + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[position + 3 : position + 5], "big")
            width = int.from_bytes(data[position + 5 : position + 7], "big")
            if width and height:
                return width, height
        position += length
    raise ValueError("could not read JPEG dimensions")
