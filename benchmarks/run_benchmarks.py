"""Paired scheduler microbenchmark with deterministic bootstrap uncertainty."""
from __future__ import annotations
import argparse
import json
import platform
import random
import statistics
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from chronos.engine import SimulationEngine  # noqa: E402
from chronos.events import Event  # noqa: E402
from chronos.experiments import ExperimentManifest  # noqa: E402

def chronos_workload(n: int) -> None:
    engine=SimulationEngine("benchmark")
    engine.register("noop",lambda event,simulation: None)
    for i in range(n): engine.schedule(i%100,"noop",{"index":i})
    engine.run()

def reference_workload(n: int) -> None:
    pending=[(i%100,i,Event(f"reference:{i}",i%100,i,"noop",{"index":i})) for i in range(n)]
    pending.sort(key=lambda row:(row[0],row[1]))
    for _time,_seq,event in pending:
        _=event.payload["index"]

def timed(fn,n):
    start=time.perf_counter(); fn(n); return time.perf_counter()-start

def bootstrap_median_ci(differences: list[float], seed: int, draws: int=4000) -> list[float]:
    rng=random.Random(seed); n=len(differences); estimates=[]
    for _ in range(draws):
        sample=[differences[rng.randrange(n)] for _ in range(n)]
        estimates.append(statistics.median(sample))
    estimates.sort()
    return [estimates[int(0.025*draws)],estimates[min(draws-1,int(0.975*draws))]]

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--events",type=int,default=10000)
    parser.add_argument("--warmups",type=int,default=2)
    parser.add_argument("--repeats",type=int,default=15)
    parser.add_argument("--seed",type=int,default=20261104)
    parser.add_argument("--output",type=Path,default=Path("benchmark-results/chronos.json"))
    args=parser.parse_args()
    if args.events<1 or args.warmups<0 or args.repeats<3: parser.error("events positive, warmups non-negative, repeats at least 3")
    manifest=ExperimentManifest.create("scheduler-paired-noop-v2",seed=args.seed,
        parameters={"events":args.events,"warmups":args.warmups,"repeats":args.repeats},
        workload="schedule and dispatch equal-count no-op events with equivalent payload construction")
    for _ in range(args.warmups):
        chronos_workload(args.events); reference_workload(args.events)
    chrono=[]; reference=[]
    for i in range(args.repeats):
        pair=[("chronos",chronos_workload),("reference",reference_workload)]
        if i%2: pair.reverse()
        values={}
        for name,fn in pair: values[name]=timed(fn,args.events)
        chrono.append(values["chronos"]); reference.append(values["reference"])
    diffs=[a-b for a,b in zip(chrono,reference,strict=True)]
    result={"manifest":json.loads(manifest.to_json()),
        "runtime":{"python":platform.python_version(),"platform":platform.platform()},
        "paired_samples_seconds":{"chronos":chrono,"reference":reference,"chronos_minus_reference":diffs},
        "summary":{"chronos_median":statistics.median(chrono),"reference_median":statistics.median(reference),
            "paired_median_difference":statistics.median(diffs),
            "paired_median_difference_bootstrap_95_percent_ci":bootstrap_median_ci(diffs,args.seed),
            "bootstrap_draws":4000,"bootstrap_seed":args.seed},
        "methodology":{"warmups_excluded":True,"run_order":"alternating","clock":"perf_counter",
            "processes":1,"baseline":"sorted-list reference with Event and payload construction plus dispatch iteration",
            "interpretation":"single-machine paired microbenchmark; bootstrap interval does not remove systematic bias"}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__=="__main__": main()
