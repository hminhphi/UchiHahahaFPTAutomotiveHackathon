"""Detect phone use from a live webcam until the user presses q."""

import argparse

import cv2
from ultralytics import YOLO

from fleetiq_training_dms.phone_detector import PhoneUseSmoother


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect phone use from a live camera")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--confidence", type=float, default=0.40)
    args = parser.parse_args()

    model = YOLO(args.model)
    smoother = PhoneUseSmoother()
    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        raise SystemExit(f"Could not open camera index {args.camera}")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                break

            result = model.predict(source=frame, verbose=False)[0]
            detected = any(
                result.names[int(class_id)] == "cell phone" and score >= args.confidence
                for class_id, score in zip(result.boxes.cls.tolist(), result.boxes.conf.tolist(), strict=True)
            )
            phone_use = smoother.update(detected)
            label = "PHONE USE: DETECTED" if phone_use else "PHONE USE: NOT DETECTED"
            color = (0, 80, 255) if phone_use else (40, 180, 40)
            annotated = result.plot()
            cv2.putText(annotated, label, (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(annotated, "Press q to quit", (20, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow("FleetIQ phone-use detection", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
