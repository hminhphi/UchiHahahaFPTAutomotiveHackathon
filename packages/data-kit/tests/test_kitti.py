from __future__ import annotations

from pathlib import Path

from fleetiq_data.kitti import find_frame, parse_kitti_labels


def test_parse_kitti_labels_preserves_standard_fields(tmp_path: Path) -> None:
    labels = tmp_path / "000007.txt"
    labels.write_text(
        "Car 0.0 0 0.1 10 20 30 40 1.5 1.6 4.0 1.0 1.5 12.0 0.2 0.9\n",
        encoding="utf-8",
    )

    parsed = parse_kitti_labels(labels)

    assert len(parsed) == 1
    assert parsed[0].object_type == "Car"
    assert parsed[0].bbox == (10.0, 20.0, 30.0, 40.0)
    assert parsed[0].score == 0.9


def test_find_frame_resolves_images_and_sparse_depth(tmp_path: Path) -> None:
    images = tmp_path / "image_2"
    depth = tmp_path / "depth"
    images.mkdir()
    depth.mkdir()
    (images / "000007.png").touch()
    (depth / "000000.npy").touch()
    (depth / "000010.npy").touch()

    assert find_frame(images, 7) == images / "000007.png"
    assert find_frame(depth, 7, suffixes=(".npy",), policy="previous") == depth / "000000.npy"
    assert find_frame(depth, 7, suffixes=(".npy",), policy="nearest") == depth / "000010.npy"


def test_parse_kitti_labels_skips_non_finite_and_fractional_occlusion_rows(tmp_path: Path) -> None:
    labels = tmp_path / "000007.txt"
    labels.write_text(
        "Car 0.0 1.5 0.1 10 20 30 40 1.5 1.6 4.0 1.0 1.5 12.0 0.2\n"
        "Car nan 0 0.1 10 20 30 40 1.5 1.6 4.0 1.0 1.5 12.0 0.2\n"
        "Car 0.0 0 0.1 10 20 30 40 1.5 1.6 4.0 1.0 1.5 12.0 0.2 inf\n"
        "Car 0.0 2 0.1 10 20 30 40 1.5 1.6 4.0 1.0 1.5 12.0 0.2\n",
        encoding="utf-8",
    )

    parsed = parse_kitti_labels(labels)

    assert len(parsed) == 1
    assert parsed[0].occluded == 2


def test_find_frame_previous_does_not_use_a_future_frame(tmp_path: Path) -> None:
    depth = tmp_path / "depth"
    depth.mkdir()
    (depth / "000010.npy").touch()

    assert find_frame(depth, 5, suffixes=(".npy",), policy="previous") is None
    assert find_frame(depth, 5, suffixes=(".npy",), policy="nearest") == depth / "000010.npy"
