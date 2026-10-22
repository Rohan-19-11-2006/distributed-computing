"""Unit tests - run with:  python -m unittest test_sim -v"""
import random
import unittest

import sync_async_sim as sim


def tiny(n=4):
    """Fast deterministic workload (small delays) for quick tests."""
    return [sim.Process(i, 0.01, 0.05, 0.01) for i in range(n)]


class TestSimulation(unittest.TestCase):
    def test_sync_runs_sequentially(self):
        log = []
        total = sim.run_synchronous(tiny(4), log)
        starts_ends = sorted(log, key=lambda r: r[0])
        for prev, cur in zip(starts_ends, starts_ends[1:]):
            self.assertGreaterEqual(cur[1], prev[2] - 1e-3)   # starts after prev ends
        self.assertGreaterEqual(total, 4 * 0.07 - 0.01)

    def test_async_overlaps(self):
        log = []
        total = sim.run_asynchronous(tiny(4), log)
        self.assertLess(total, 4 * 0.07)                       # far below sequential sum
        self.assertTrue(all(t0 < 0.03 for _, t0, _ in log))    # all start ~together

    def test_async_faster_than_sync(self):
        s, a, _, _ = sim.experiment(4, random.Random(1))
        self.assertLess(a, s)

    def test_every_process_logged_once(self):
        for runner in (sim.run_synchronous, sim.run_asynchronous):
            log = []
            runner(tiny(5), log)
            self.assertEqual(sorted(pid for pid, _, _ in log), list(range(5)))
            self.assertTrue(all(t1 >= t0 for _, t0, t1 in log))

    def test_zero_processes(self):
        for runner in (sim.run_synchronous, sim.run_asynchronous):
            log = []
            runner([], log)
            self.assertEqual(log, [])

    def test_reproducible_workload(self):
        a = sim.make_processes(5, random.Random(42))
        b = sim.make_processes(5, random.Random(42))
        self.assertEqual([(p.compute_time, p.comm_delay) for p in a],
                         [(p.compute_time, p.comm_delay) for p in b])


if __name__ == "__main__":
    unittest.main()
