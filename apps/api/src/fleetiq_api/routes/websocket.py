"""Camera ingress and latest-state WebSocket routes."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..dependencies import AppDependencies
from ..ws.frame_protocol import FrameProtocolError, decode_camera_frame

router = APIRouter()


@router.websocket("/ws/v1/trips/{trip_id}/camera/{view}")
async def camera_stream(
    websocket: WebSocket,
    trip_id: str,
    view: str,
    role: str = "viewer",
) -> None:
    await websocket.accept()
    settings = websocket.app.state.settings
    dependencies: AppDependencies = websocket.app.state.dependencies
    if role == "producer":
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                payload = message.get("bytes")
                if payload is None:
                    await websocket.close(code=1003, reason="binary camera frames required")
                    return
                try:
                    frame = decode_camera_frame(
                        payload,
                        settings.max_metadata_bytes,
                        settings.max_frame_bytes,
                    )
                except FrameProtocolError as error:
                    await websocket.close(code=error.close_code, reason=str(error))
                    return
                await dependencies.camera_sink.publish(trip_id, view, frame, payload)
                await websocket.send_json(
                    {
                        "schema_version": "1.0",
                        "status": "accepted",
                        "trip_id": trip_id,
                        "view": view,
                        "frame_index": frame.metadata.frame_index,
                        "correlation_id": frame.metadata.correlation_id,
                    }
                )
        except WebSocketDisconnect:
            return

    subscription = await dependencies.camera_sink.subscribe(trip_id, view)
    replay_lease = await dependencies.camera_replay.acquire(trip_id, view, dependencies.camera_sink)
    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive())
            frame_task = asyncio.create_task(subscription.queue.get())
            done, pending = await asyncio.wait(
                {receive_task, frame_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if frame_task in done:
                await websocket.send_bytes(frame_task.result())
            if receive_task in done:
                message = receive_task.result()
                if message["type"] == "websocket.disconnect":
                    return
                payload = message.get("bytes")
                if payload is None:
                    await websocket.close(code=1003, reason="binary camera frames required")
                    return
                try:
                    frame = decode_camera_frame(
                        payload,
                        settings.max_metadata_bytes,
                        settings.max_frame_bytes,
                    )
                except FrameProtocolError as error:
                    await websocket.close(code=error.close_code, reason=str(error))
                    return
                await dependencies.camera_sink.publish(
                    trip_id,
                    view,
                    frame,
                    payload,
                    exclude=subscription.queue,
                )
                await websocket.send_json(
                    {
                        "schema_version": "1.0",
                        "status": "accepted",
                        "trip_id": trip_id,
                        "view": view,
                        "frame_index": frame.metadata.frame_index,
                        "correlation_id": frame.metadata.correlation_id,
                    }
                )
    except WebSocketDisconnect:
        return
    finally:
        await replay_lease.close()
        await subscription.close()


@router.websocket("/ws/v1/trips/{trip_id}/live")
async def live_state(websocket: WebSocket, trip_id: str) -> None:
    await websocket.accept()
    dependencies: AppDependencies = websocket.app.state.dependencies
    subscription = await dependencies.live_state.subscribe(trip_id)
    try:
        while True:
            state_task = asyncio.create_task(subscription.queue.get())
            receive_task = asyncio.create_task(websocket.receive())
            done, pending = await asyncio.wait(
                {state_task, receive_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if receive_task in done:
                message = receive_task.result()
                if message["type"] == "websocket.disconnect":
                    return
            if state_task in done:
                await websocket.send_json(state_task.result())
    except WebSocketDisconnect:
        return
    finally:
        await subscription.close()
