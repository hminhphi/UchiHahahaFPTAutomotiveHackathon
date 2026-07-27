from __future__ import annotations

import unittest

from scripts.roadface.relabel_locateanything import (
    LocatedBox,
    deduplicate_boxes,
    kitti_2d_line,
    parse_locateanything_answer,
)


class LocateAnythingLabelTests(unittest.TestCase):
    def test_parses_multiple_categories_and_boxes(self) -> None:
        answer = (
            "<ref>car</ref><box><100><200><300><600></box>"
            "<box><400><300><500><700></box>"
            "<ref>person or pedestrian</ref><box><700><100><800><900></box>"
        )
        boxes = parse_locateanything_answer(answer, 640, 360)
        self.assertEqual([box.object_type for box in boxes], ["Car", "Car", "Pedestrian"])
        self.assertEqual(boxes[0].bbox, (64.0, 72.0, 192.0, 216.0))

    def test_specific_vehicle_wins_cross_class_duplicate(self) -> None:
        boxes = [
            LocatedBox("Car", (10, 10, 100, 100), "car"),
            LocatedBox("LongVehicle", (11, 11, 101, 101), "truck"),
        ]
        kept = deduplicate_boxes(boxes)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].object_type, "LongVehicle")

    def test_truncates_runaway_adjacent_box_tail(self) -> None:
        answer = (
            "<ref>car</ref>"
            "<box><100><400><200><500></box>"
            "<box><500><497><520><517></box>"
            "<box><520><497><540><517></box>"
            "<box><540><497><560><517></box>"
            "<box><560><497><580><517></box>"
            "<box><580><497><600><517></box>"
        )
        boxes = parse_locateanything_answer(answer, 1000, 1000)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].bbox, (100.0, 400.0, 200.0, 500.0))

    def test_writes_kitti_2d_sentinels(self) -> None:
        line = kitti_2d_line(LocatedBox("Bus", (1, 2, 30, 40), "bus"))
        fields = line.split()
        self.assertEqual(fields[0], "Bus")
        self.assertEqual(len(fields), 15)
        self.assertEqual(fields[4:8], ["1.00", "2.00", "30.00", "40.00"])


if __name__ == "__main__":
    unittest.main()
