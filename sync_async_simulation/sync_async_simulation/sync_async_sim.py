"""
sync_async_sim.py
=================
Simulation comparing SYNCHRONOUS and ASYNCHRONOUS execution of
communicating processes.

Each simulated process performs:
    1. local computation      (compute_time)
    2. a communication step   (comm_delay)   e.g. network / IPC latency
    3. response handling      (response_time)

SYNCHRONOUS : the caller blocks; process i must fully finish (including
              waiting for its communication delay) before process i+1 starts.
ASYNCHRONOUS: all processes are dispatched together on an asyncio event
              loop, so communication delays overlap.

Usage
-----
    python sync_async_sim.py                 # default demo + scalability test
    python sync_async_sim.py --n 8           # detailed run with 8 processes
    python sync_async_sim.py --sizes 1 2 4 8 --trials 2
    python sync_async_sim.py --no-plots      # skip chart generation
    python sync_async_sim.py --seed 7        # different random workload
"""

import argparse
import asyncio
import random
import statistics
import time


class Process:
    """A simulated process with compute, communication and response costs."""

    def __init__(self, pid, compute_time, comm_delay, response_time):
        self.pid = pid
        self.compute_time = compute_time
        self.comm_delay = comm_delay
        self.response_time = response_time

    def __repr__(self):
        return (f"P{self.pid}(cpu={self.compute_time:.2f}, "
                f"comm={self.comm_delay:.2f}, resp={self.response_time:.2f})")


def make_processes(n, rng):
    """Create n processes with randomised costs (seconds)."""
    return [
        Process(i,
                rng.uniform(0.05, 0.15),
                rng.uniform(0.20, 0.50),
                rng.uniform(0.05, 0.10))
        for i in range(n)
    ]


def clone(processes):
    """Identical workload copy so both models are compared fairly."""
    return [Process(p.pid, p.compute_time, p.comm_delay, p.response_time)
            for p in processes]


# ------------------------------------------------------------------
# SYNCHRONOUS EXECUTION  (blocking)
# ------------------------------------------------------------------
def run_synchronous(processes, log):
    start = time.perf_counter()
    for p in processes:
        t0 = time.perf_counter()
        time.sleep(p.compute_time)     # local computation
        time.sleep(p.comm_delay)       # BLOCKING communication
        time.sleep(p.response_time)    # handle response
        t1 = time.perf_counter()
        log.append((p.pid, t0 - start, t1 - start))
    return time.perf_counter() - start


# ------------------------------------------------------------------
# ASYNCHRONOUS EXECUTION  (non-blocking, event loop)
# ------------------------------------------------------------------
async def handle_process(p, log, start):
    t0 = time.perf_counter()
    await asyncio.sleep(p.compute_time)    # local computation
    await asyncio.sleep(p.comm_delay)      # NON-blocking communication
    await asyncio.sleep(p.response_time)   # handle response
    t1 = time.perf_counter()
    log.append((p.pid, t0 - start, t1 - start))


async def _run_async(processes, log):
    start = time.perf_counter()
    tasks = [asyncio.create_task(handle_process(p, log, start))
             for p in processes]
    if tasks:
        await asyncio.gather(*tasks)
    return time.perf_counter() - start


def run_asynchronous(processes, log):
    return asyncio.run(_run_async(processes, log))


# ------------------------------------------------------------------
# EXPERIMENT HELPERS
# ------------------------------------------------------------------
def experiment(n, rng):
    sync_procs = make_processes(n, rng)
    async_procs = clone(sync_procs)
    sync_log, async_log = [], []
    sync_time = run_synchronous(sync_procs, sync_log)
    async_time = run_asynchronous(async_procs, async_log)
    return sync_time, async_time, sync_log, async_log


def detailed_run(n, rng):
    sync_time, async_time, sync_log, async_log = experiment(n, rng)
    print(f"\n--- Detailed run: {n} processes ---")
    print("\nSynchronous timeline (each process waits for the previous one):")
    for pid, t0, t1 in sorted(sync_log):
        print(f"  P{pid}: start={t0:6.3f}s  end={t1:6.3f}s")
    print(f"  TOTAL synchronous time  = {sync_time:6.3f} s")

    print("\nAsynchronous timeline (communication delays overlap):")
    for pid, t0, t1 in sorted(async_log):
        print(f"  P{pid}: start={t0:6.3f}s  end={t1:6.3f}s")
    print(f"  TOTAL asynchronous time = {async_time:6.3f} s")

    speedup = sync_time / async_time if async_time else float("inf")
    print(f"\nSpeedup (sync/async) for N={n}: {speedup:.2f}x")
    return sync_log, async_log


def scalability(sizes, trials, rng):
    print("\n" + "=" * 70)
    print("SCALABILITY TEST: increasing number of simulated processes")
    print("=" * 70)
    print(f"{'N':<6}{'Sync Time(s)':<16}{'Async Time(s)':<16}{'Speedup':<10}")
    sync_avgs, async_avgs = [], []
    for n in sizes:
        s_times, a_times = [], []
        for _ in range(trials):
            s, a, _, _ = experiment(n, rng)
            s_times.append(s)
            a_times.append(a)
        s_avg, a_avg = statistics.mean(s_times), statistics.mean(a_times)
        sync_avgs.append(s_avg)
        async_avgs.append(a_avg)
        print(f"{n:<6}{s_avg:<16.3f}{a_avg:<16.3f}{s_avg / a_avg:<10.2f}")
    return sync_avgs, async_avgs


# ------------------------------------------------------------------
# PLOTS (optional - needs matplotlib)
# ------------------------------------------------------------------
def make_plots(sizes, sync_avgs, async_avgs, sync_log, async_log):
    try:
        import matplotlib
        matplotlib.use("Agg")          # works without a display
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n[info] matplotlib not installed - skipping charts. "
              "Install with: pip install matplotlib")
        return

    # 1. line chart
    plt.figure(figsize=(7, 4.5))
    plt.plot(sizes, sync_avgs, marker="o", label="Synchronous", color="#c0392b")
    plt.plot(sizes, async_avgs, marker="s", label="Asynchronous", color="#2471a3")
    plt.xlabel("Number of Simulated Processes (N)")
    plt.ylabel("Total Execution Time (s)")
    plt.title("Synchronous vs Asynchronous Execution Time")
    plt.legend(); plt.grid(True, linestyle="--", alpha=0.5); plt.tight_layout()
    plt.savefig("execution_time_comparison.png", dpi=150); plt.close()

    # 2. bar chart
    plt.figure(figsize=(7, 4.5))
    w = 0.35
    x = list(range(len(sizes)))
    plt.bar([i - w / 2 for i in x], sync_avgs, w, label="Synchronous", color="#c0392b")
    plt.bar([i + w / 2 for i in x], async_avgs, w, label="Asynchronous", color="#2471a3")
    plt.xticks(x, sizes)
    plt.xlabel("Number of Simulated Processes (N)")
    plt.ylabel("Total Execution Time (s)")
    plt.title("Execution Time Comparison (Bar Chart)")
    plt.legend(); plt.tight_layout()
    plt.savefig("execution_time_bar.png", dpi=150); plt.close()

    # 3. Gantt-style timeline for the detailed run
    colors = ["#c0392b", "#e67e22", "#f1c40f", "#27ae60", "#2980b9",
              "#8e44ad", "#16a085", "#7f8c8d"]
    fig, axes = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    for ax, log, title in ((axes[0], sync_log, "Synchronous Execution Timeline"),
                           (axes[1], async_log, "Asynchronous Execution Timeline")):
        for pid, t0, t1 in sorted(log):
            ax.barh(f"P{pid}", t1 - t0, left=t0,
                    color=colors[pid % len(colors)], edgecolor="black")
        ax.set_title(title)
    axes[1].set_xlabel("Time (s)")
    plt.tight_layout()
    plt.savefig("timeline_comparison.png", dpi=150); plt.close()

    print("\nCharts saved: execution_time_comparison.png, "
          "execution_time_bar.png, timeline_comparison.png")


def main():
    ap = argparse.ArgumentParser(description="Sync vs Async execution simulation")
    ap.add_argument("--n", type=int, default=5,
                    help="processes for the detailed timeline run (default 5)")
    ap.add_argument("--sizes", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32],
                    help="process counts for the scalability test")
    ap.add_argument("--trials", type=int, default=3,
                    help="trials averaged per size (default 3)")
    ap.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    ap.add_argument("--no-plots", action="store_true", help="skip chart generation")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    print("=" * 70)
    print("SYNCHRONOUS vs ASYNCHRONOUS EXECUTION SIMULATION")
    print("=" * 70)

    sync_log, async_log = detailed_run(args.n, rng)
    sync_avgs, async_avgs = scalability(args.sizes, args.trials, rng)

    if not args.no_plots:
        make_plots(args.sizes, sync_avgs, async_avgs, sync_log, async_log)


if __name__ == "__main__":
    main()
