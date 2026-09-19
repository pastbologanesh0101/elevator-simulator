"""Reproducible random rider generation for demos and tests."""
from __future__ import annotations

import random
from typing import List

from .models import Rider


def generate_riders(
    num_riders: int,
    min_floor: int,
    max_floor: int,
    time_window: int,
    seed: int,
) -> List[Rider]:
    """Generate ``num_riders`` random (origin, destination, request_time)
    riders using a seeded RNG, so the same seed always produces the exact
    same batch of requests.
    """
    rng = random.Random(seed)
    riders: List[Rider] = []
    for i in range(num_riders):
        origin = rng.randint(min_floor, max_floor)
        destination = rng.randint(min_floor, max_floor)
        while destination == origin:
            destination = rng.randint(min_floor, max_floor)
        request_time = rng.randint(0, time_window)
        riders.append(
            Rider(
                origin_floor=origin,
                destination_floor=destination,
                request_time=request_time,
                rider_id=i,
            )
        )
    riders.sort(key=lambda r: r.request_time)
    return riders
