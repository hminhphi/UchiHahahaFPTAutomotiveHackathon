import sys
import os
from kuksa_client.grpc import VSSClient
from kuksa_client.grpc import Datapoint

import random
import time

KUKSA_PORT = int(os.environ.get("KUKSA_PORT", 55555))

def set_speed(speed_value):
    try:
        with VSSClient("127.0.0.1", KUKSA_PORT) as client:
            client.set_current_values({
                "Vehicle.Speed": Datapoint(float(speed_value))
            })
            print(f"Set Vehicle.Speed to {speed_value} km/h")
    except Exception as e:
        print(f"Failed: {e}")

def run_random():
    print("Starting random speed generator... Press Ctrl+C to stop.")
    current_speed = 60.0
    while True:
        # Thay đổi tốc độ ngẫu nhiên từ -15 đến +20
        current_speed += random.uniform(-15, 20)
        current_speed = max(0, min(120, current_speed)) # Giới hạn 0 - 120 km/h
        set_speed(current_speed)
        time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "random":
        run_random()
    elif len(sys.argv) > 1:
        set_speed(sys.argv[1])
    else:
        print("Usage: uv run python scripts/mock_vehicle.py <speed | random>")

