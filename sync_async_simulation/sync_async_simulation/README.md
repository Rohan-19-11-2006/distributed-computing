# Synchronous vs Asynchronous Execution Simulation

Simulates N processes, each doing local computation, a communication step
(with delay) and response handling, and runs the *same* workload under:

* **Synchronous** model - blocking, one process after another (`time.sleep`)
* **Asynchronous** model - non-blocking event loop (`asyncio`), delays overlap

## Requirements
* Python 3.8+
* `matplotlib` (only for the charts; the simulation itself uses the standard library)

```
pip install -r requirements.txt
```

## Run
```
python sync_async_sim.py                      # full demo (takes ~40 s)
python sync_async_sim.py --n 8                # timeline run with 8 processes
python sync_async_sim.py --sizes 1 2 4 8 --trials 2   # faster scalability test
python sync_async_sim.py --no-plots           # console output only
```
Charts are written to the current folder:
`execution_time_comparison.png`, `execution_time_bar.png`, `timeline_comparison.png`.

## Test
```
python -m unittest test_sim -v
```

## Files
| File | Purpose |
|------|---------|
| `sync_async_sim.py` | Simulation, experiments and charts |
| `test_sim.py` | Unit tests |
| `requirements.txt` | Dependencies |
