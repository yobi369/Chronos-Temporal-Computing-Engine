"""Compare Chronos with a simple sorted-list reference scheduler."""
from __future__ import annotations
import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from chronos.engine import SimulationEngine  # noqa: E402
from chronos.experiments import ExperimentManifest  # noqa: E402

def chronos_workload(event_count: int) -> None:
    engine = SimulationEngine("benchmark")
    engine.register("noop", lambda event, simulation: None)
    for index in range(event_count):
        engine.schedule(index % 100, "noop", {"index": index})
    engine.run()

def reference_workload(event_count: int) -> None:
    pending = [(index % 100, index) for index in range(event_count)]
    pending.sort(key=lambda item: (item[0], item[1]))
    for _logical_time, _sequence in pending:
        pass

def measure(function, event_count: int, warmups: int, repeats: int) -> list[float]:
    for _ in range(warmups):
        function(event_count)
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        function(event_count)
        samples.append(time.perf_counter() - start)
    return samples

def summarize(samples: list[float], event_count: int) -> dict[str, object]:
    median = statistics.median(samples)
    return {"samples_seconds": samples, "min_seconds": min(samples),
        "median_seconds": median, "mean_seconds": statistics.mean(samples),
        "max_seconds": max(samples), "median_events_per_second": event_count / median}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=10_000)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--output", type=Path, default=Path("benchmark-results/chronos.json"))
    args = parser.parse_args()
    if args.events < 1 or args.warmups < 0 or args.repeats < 1:
        parser.error("events/repeats must be positive and warmups non-negative")
    manifest = ExperimentManifest.create("scheduler-noop-v1", seed=args.seed,
        parameters={"events": args.events, "warmups": args.warmups, "repeats": args.repeats},
        workload="schedule N no-op events across 100 logical-time buckets")
    chronos_samples = measure(chronos_workload, args.events, args.warmups, args.repeats)
    reference_samples = measure(reference_workload, args.events, args.warmups, args.repeats)
    result = {"manifest": json.loads(manifest.to_json()),
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "implementations": {
            "chronos_heap_scheduler": summarize(chronos_samples, args.events),
            "reference_sorted_list": summarize(reference_samples, args.events)},
        "methodology": {"clock": "time.perf_counter", "warmups_excluded": True,
            "repetitions": args.repeats, "single_process": True,
            "reference_model": "sort by (logical_time, insertion_sequence)",
            "comparative_claims": "microbenchmark only; no statistical significance analysis"}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, indent=2))

if __name__ == "__main__":
    main()
