"""Unit tests for the dispatch strategies."""
import unittest

from elevator_simulator.building import Building, InvalidFloorError
from elevator_simulator.dispatch import NearestElevatorDispatch, ScanDispatch
from elevator_simulator.models import Direction, Elevator, Rider


class TestNearestElevatorDispatch(unittest.TestCase):
    def test_assigns_hall_call_to_genuinely_closest_elevator(self):
        """Three elevators at floors 0, 5, and 9. A hall call at floor 6
        should go to the elevator at floor 5 (distance 1), not the one at
        floor 0 (distance 6) or floor 9 (distance 3)."""
        e_far = Elevator(elevator_id=0, current_floor=0, capacity=4)
        e_near = Elevator(elevator_id=1, current_floor=5, capacity=4)
        e_mid = Elevator(elevator_id=2, current_floor=9, capacity=4)
        elevators = [e_far, e_near, e_mid]

        rider = Rider(origin_floor=6, destination_floor=12, request_time=0)
        strategy = NearestElevatorDispatch()
        chosen = strategy.assign(elevators, rider)

        self.assertIs(chosen, e_near)

    def test_skips_full_elevators(self):
        """A closer elevator that is at capacity must be skipped in favour
        of a farther elevator that still has room."""
        full = Elevator(elevator_id=0, current_floor=5, capacity=1)
        full.riders.append(Rider(origin_floor=5, destination_floor=9, request_time=0))
        has_room = Elevator(elevator_id=1, current_floor=0, capacity=4)

        rider = Rider(origin_floor=6, destination_floor=12, request_time=0)
        strategy = NearestElevatorDispatch()
        chosen = strategy.assign([full, has_room], rider)

        self.assertIs(chosen, has_room)

    def test_no_elevator_available_when_all_full(self):
        full = Elevator(elevator_id=0, current_floor=5, capacity=1)
        full.riders.append(Rider(origin_floor=5, destination_floor=9, request_time=0))
        rider = Rider(origin_floor=6, destination_floor=12, request_time=0)

        strategy = NearestElevatorDispatch()
        self.assertIsNone(strategy.assign([full], rider))

    def test_greedy_direction_toward_nearest_stop(self):
        elevator = Elevator(elevator_id=0, current_floor=5, capacity=4, direction=Direction.IDLE)
        elevator.assigned_pickups.append(Rider(origin_floor=8, destination_floor=1, request_time=0))
        strategy = NearestElevatorDispatch()
        self.assertEqual(strategy.next_direction(elevator, 0, 20), Direction.UP)


class TestScanDispatch(unittest.TestCase):
    def test_does_not_reverse_while_compatible_requests_remain_ahead(self):
        """An elevator moving UP with a stop still ahead of it (further up)
        must keep moving UP, even though it also owes a stop behind it."""
        elevator = Elevator(elevator_id=0, current_floor=5, capacity=4, direction=Direction.UP)
        elevator.assigned_pickups.append(Rider(origin_floor=8, destination_floor=12, request_time=0))
        elevator.assigned_pickups.append(Rider(origin_floor=2, destination_floor=0, request_time=0))

        strategy = ScanDispatch()
        # Floor 8 (ahead, up) is outstanding, so the elevator must not
        # reverse toward floor 2 (behind) yet.
        self.assertEqual(strategy.next_direction(elevator, 0, 20), Direction.UP)

    def test_reverses_once_nothing_left_ahead(self):
        """Once the only outstanding stop is behind the elevator, it must
        reverse direction."""
        elevator = Elevator(elevator_id=0, current_floor=8, capacity=4, direction=Direction.UP)
        elevator.assigned_pickups.append(Rider(origin_floor=2, destination_floor=0, request_time=0))

        strategy = ScanDispatch()
        self.assertEqual(strategy.next_direction(elevator, 0, 20), Direction.DOWN)

    def test_idle_when_no_stops(self):
        elevator = Elevator(elevator_id=0, current_floor=8, capacity=4, direction=Direction.UP)
        strategy = ScanDispatch()
        self.assertEqual(strategy.next_direction(elevator, 0, 20), Direction.IDLE)

    def test_prefers_elevator_already_sweeping_toward_call(self):
        sweeping = Elevator(elevator_id=0, current_floor=2, capacity=4, direction=Direction.UP)
        idle_far = Elevator(elevator_id=1, current_floor=0, capacity=4, direction=Direction.IDLE)
        # idle_far is technically closer in raw distance to floor 3 than it
        # is to floor... but sweeping is already heading that way, and is
        # closer too, so it should win.
        rider = Rider(origin_floor=3, destination_floor=10, request_time=0)
        strategy = ScanDispatch()
        chosen = strategy.assign([sweeping, idle_far], rider)
        self.assertIs(chosen, sweeping)


class TestBuildingFloorValidation(unittest.TestCase):
    def test_rejects_floor_above_top(self):
        building = Building(num_floors=10, num_elevators=1)  # floors 0..9
        with self.assertRaises(InvalidFloorError):
            building.validate_floor(10)

    def test_rejects_floor_below_ground(self):
        building = Building(num_floors=10, num_elevators=1, ground_floor=0)
        with self.assertRaises(InvalidFloorError):
            building.validate_floor(-1)

    def test_is_valid_request_handles_out_of_range_gracefully(self):
        building = Building(num_floors=10, num_elevators=1)
        self.assertFalse(building.is_valid_request(0, 99))
        self.assertFalse(building.is_valid_request(-5, 3))
        self.assertTrue(building.is_valid_request(0, 9))

    def test_same_floor_request_is_invalid(self):
        building = Building(num_floors=10, num_elevators=1)
        self.assertFalse(building.is_valid_request(4, 4))


if __name__ == "__main__":
    unittest.main()
