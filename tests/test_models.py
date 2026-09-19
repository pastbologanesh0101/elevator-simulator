"""Unit tests for the core Rider / Elevator models."""
import unittest

from elevator_simulator.models import Direction, Elevator, Rider, can_drop_off, can_pick_up


class TestRider(unittest.TestCase):
    def test_direction_up(self):
        rider = Rider(origin_floor=2, destination_floor=9, request_time=0)
        self.assertEqual(rider.direction, Direction.UP)

    def test_direction_down(self):
        rider = Rider(origin_floor=9, destination_floor=2, request_time=0)
        self.assertEqual(rider.direction, Direction.DOWN)

    def test_wait_and_travel_time_known_scenario(self):
        # Crafted scenario: rider requests at t=5, is picked up at t=9,
        # dropped off at t=17.
        rider = Rider(origin_floor=0, destination_floor=8, request_time=5)
        rider.pickup_time = 9
        rider.dropoff_time = 17
        self.assertEqual(rider.wait_time, 4)
        self.assertEqual(rider.travel_time, 8)
        self.assertEqual(rider.total_time, 12)

    def test_wait_time_none_before_pickup(self):
        rider = Rider(origin_floor=0, destination_floor=8, request_time=5)
        self.assertIsNone(rider.wait_time)
        self.assertIsNone(rider.travel_time)


class TestElevatorPickup(unittest.TestCase):
    def test_pickup_when_reaches_floor_with_matching_direction(self):
        """An elevator moving UP that reaches a rider's floor, where the
        rider also wants to go UP, should be able to pick them up."""
        elevator = Elevator(elevator_id=0, current_floor=3, capacity=4, direction=Direction.UP)
        rider = Rider(origin_floor=3, destination_floor=10, request_time=0)  # wants UP
        elevator.assigned_pickups.append(rider)

        self.assertTrue(can_pick_up(elevator, rider))

    def test_no_pickup_when_direction_incompatible(self):
        """An elevator moving UP should not board a rider who wants to go DOWN,
        even if it is sitting at their floor."""
        elevator = Elevator(elevator_id=0, current_floor=3, capacity=4, direction=Direction.UP)
        rider = Rider(origin_floor=3, destination_floor=0, request_time=0)  # wants DOWN
        elevator.assigned_pickups.append(rider)

        self.assertFalse(can_pick_up(elevator, rider))

    def test_no_pickup_when_not_at_rider_floor(self):
        elevator = Elevator(elevator_id=0, current_floor=3, capacity=4, direction=Direction.UP)
        rider = Rider(origin_floor=5, destination_floor=10, request_time=0)
        self.assertFalse(can_pick_up(elevator, rider))

    def test_idle_elevator_can_pick_up_regardless_of_rider_direction(self):
        elevator = Elevator(elevator_id=0, current_floor=3, capacity=4, direction=Direction.IDLE)
        rider = Rider(origin_floor=3, destination_floor=0, request_time=0)  # wants DOWN
        self.assertTrue(can_pick_up(elevator, rider))

    def test_capacity_respected(self):
        """A full elevator must not pick up additional riders until it has space."""
        elevator = Elevator(elevator_id=0, current_floor=3, capacity=2, direction=Direction.UP)
        elevator.riders = [
            Rider(origin_floor=0, destination_floor=9, request_time=0),
            Rider(origin_floor=1, destination_floor=9, request_time=0),
        ]
        waiting_rider = Rider(origin_floor=3, destination_floor=9, request_time=0)

        self.assertFalse(elevator.has_capacity())
        self.assertFalse(can_pick_up(elevator, waiting_rider))

        # Freeing a seat should make the elevator eligible again.
        elevator.riders.pop()
        self.assertTrue(elevator.has_capacity())
        self.assertTrue(can_pick_up(elevator, waiting_rider))


class TestElevatorDropoff(unittest.TestCase):
    def test_dropoff_at_destination(self):
        elevator = Elevator(elevator_id=0, current_floor=9, capacity=4, direction=Direction.UP)
        rider = Rider(origin_floor=0, destination_floor=9, request_time=0)
        elevator.riders.append(rider)

        self.assertTrue(can_drop_off(elevator, rider))

    def test_no_dropoff_before_destination(self):
        elevator = Elevator(elevator_id=0, current_floor=5, capacity=4, direction=Direction.UP)
        rider = Rider(origin_floor=0, destination_floor=9, request_time=0)
        elevator.riders.append(rider)

        self.assertFalse(can_drop_off(elevator, rider))


if __name__ == "__main__":
    unittest.main()
