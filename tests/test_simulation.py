"""Integration tests for the full discrete-event simulation loop."""
import unittest

from elevator_simulator.building import Building
from elevator_simulator.dispatch import NearestElevatorDispatch, ScanDispatch
from elevator_simulator.generator import generate_riders
from elevator_simulator.models import Rider
from elevator_simulator.simulation import Simulation


class TestSingleRiderScenario(unittest.TestCase):
    def test_wait_and_travel_time_for_known_single_rider(self):
        """One elevator starts at floor 0. A single rider requests a ride
        from floor 3 to floor 8 at t=0. The elevator must travel 3 floors to
        reach the rider (wait time 3) and then 5 more floors to the
        destination (travel time 5), one floor per tick.
        """
        building = Building(num_floors=15, num_elevators=1, capacity=4)
        sim = Simulation(building, NearestElevatorDispatch())
        rider = Rider(origin_floor=3, destination_floor=8, request_time=0)

        result = sim.run([rider])

        self.assertEqual(result.completed_count(), 1)
        served = result.riders[0]
        self.assertEqual(served.pickup_time, 3)
        self.assertEqual(served.dropoff_time, 8)
        self.assertEqual(served.wait_time, 3)
        self.assertEqual(served.travel_time, 5)

    def test_rider_request_delayed_start(self):
        """If the rider requests later (t=10) the elevator can't start
        moving toward them until that tick."""
        building = Building(num_floors=15, num_elevators=1, capacity=4)
        sim = Simulation(building, NearestElevatorDispatch())
        rider = Rider(origin_floor=3, destination_floor=8, request_time=10)

        result = sim.run([rider])
        served = result.riders[0]
        self.assertEqual(served.pickup_time, 13)  # 10 + 3 floors to travel
        self.assertEqual(served.wait_time, 3)
        self.assertEqual(served.dropoff_time, 18)
        self.assertEqual(served.travel_time, 5)


class TestInvalidRequests(unittest.TestCase):
    def test_floor_above_top_is_rejected_gracefully(self):
        building = Building(num_floors=10, num_elevators=2, capacity=4)  # floors 0..9
        sim = Simulation(building, NearestElevatorDispatch())
        bad_rider = Rider(origin_floor=3, destination_floor=50, request_time=0)
        good_rider = Rider(origin_floor=2, destination_floor=6, request_time=0)

        result = sim.run([bad_rider, good_rider])

        self.assertEqual(len(result.rejected), 1)
        self.assertIs(result.rejected[0], bad_rider)
        self.assertEqual(result.completed_count(), 1)
        self.assertIsNone(bad_rider.dropoff_time)

    def test_floor_below_ground_is_rejected_gracefully(self):
        building = Building(num_floors=10, num_elevators=2, capacity=4)
        sim = Simulation(building, NearestElevatorDispatch())
        bad_rider = Rider(origin_floor=-4, destination_floor=5, request_time=0)

        # Must not raise -- invalid requests are handled, not fatal.
        result = sim.run([bad_rider])
        self.assertEqual(len(result.rejected), 1)
        self.assertEqual(result.completed_count(), 0)


class TestCapacityUnderSimulation(unittest.TestCase):
    def test_full_elevator_does_not_overload(self):
        """With a single 1-seat elevator and two simultaneous riders at the
        same floor, only one can board per trip -- the elevator must return
        for the second."""
        building = Building(num_floors=10, num_elevators=1, capacity=1)
        sim = Simulation(building, NearestElevatorDispatch())
        r1 = Rider(origin_floor=5, destination_floor=9, request_time=0)
        r2 = Rider(origin_floor=5, destination_floor=9, request_time=0)

        result = sim.run([r1, r2])

        self.assertEqual(result.completed_count(), 2)
        # They cannot have been picked up in the same tick since capacity is 1.
        self.assertNotEqual(r1.pickup_time, r2.pickup_time)
        for e in building.elevators:
            self.assertLessEqual(e.load, e.capacity)


class TestDeterministicSeededSimulation(unittest.TestCase):
    """Same seed -> same generated riders -> same aggregate simulation
    results, every time. This is what makes the demo's comparison
    trustworthy and lets us assert on exact numbers here.
    """

    def _run(self, strategy_cls):
        riders = generate_riders(num_riders=40, min_floor=0, max_floor=14, time_window=100, seed=42)
        building = Building(num_floors=15, num_elevators=3, capacity=6)
        sim = Simulation(building, strategy_cls())
        return sim.run(riders)

    def test_generator_is_reproducible(self):
        batch_a = generate_riders(num_riders=20, min_floor=0, max_floor=9, time_window=50, seed=7)
        batch_b = generate_riders(num_riders=20, min_floor=0, max_floor=9, time_window=50, seed=7)

        self.assertEqual(len(batch_a), len(batch_b))
        for a, b in zip(batch_a, batch_b):
            self.assertEqual(a.origin_floor, b.origin_floor)
            self.assertEqual(a.destination_floor, b.destination_floor)
            self.assertEqual(a.request_time, b.request_time)

    def test_same_seed_produces_identical_aggregate_results(self):
        result_a = self._run(NearestElevatorDispatch)
        result_b = self._run(NearestElevatorDispatch)

        self.assertEqual(result_a.ticks, result_b.ticks)
        self.assertEqual(result_a.completed_count(), result_b.completed_count())
        self.assertEqual(result_a.average_wait_time(), result_b.average_wait_time())
        self.assertEqual(result_a.max_wait_time(), result_b.max_wait_time())
        self.assertEqual(result_a.average_travel_time(), result_b.average_travel_time())
        self.assertEqual(result_a.max_travel_time(), result_b.max_travel_time())

    def test_exact_aggregate_numbers_for_seed_42_nearest(self):
        """Locks in the exact numbers for seed=42 under nearest-elevator
        dispatch, so any behavioural regression in the simulation trips
        this test."""
        result = self._run(NearestElevatorDispatch)

        self.assertEqual(result.completed_count(), 40)
        self.assertEqual(result.ticks, 112)
        self.assertAlmostEqual(result.average_wait_time(), 5.05, places=4)
        self.assertEqual(result.max_wait_time(), 15)

    def test_exact_aggregate_numbers_for_seed_42_scan(self):
        result = self._run(ScanDispatch)

        self.assertEqual(result.completed_count(), 40)
        self.assertEqual(result.ticks, 106)
        self.assertAlmostEqual(result.average_wait_time(), 5.0, places=4)
        self.assertEqual(result.max_wait_time(), 18)


class TestBothStrategiesCompleteAllRiders(unittest.TestCase):
    def test_all_valid_riders_eventually_served(self):
        for strategy_cls in (NearestElevatorDispatch, ScanDispatch):
            riders = generate_riders(
                num_riders=25, min_floor=0, max_floor=11, time_window=60, seed=3
            )
            building = Building(num_floors=12, num_elevators=2, capacity=5)
            sim = Simulation(building, strategy_cls(), max_ticks=5000)
            result = sim.run(riders)
            self.assertEqual(
                result.completed_count(), 25, f"{strategy_cls.__name__} left riders unserved"
            )
            self.assertLess(result.ticks, 5000, f"{strategy_cls.__name__} hit the safety cap")


if __name__ == "__main__":
    unittest.main()
