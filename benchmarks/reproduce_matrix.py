# ruff: noqa: E501, E701, E702
"""Emit a machine-labelled independent benchmark reproduction record."""
from __future__ import annotations
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

def main() -> None:
    output=Path(os.environ.get("CHRONOS_BENCHMARK_OUTPUT","benchmark-results"))
    output.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([sys.executable,"benchmarks/run_benchmarks.py","--events","10000",
        "--warmups","2","--repeats","15","--output",str(output/"paired.json")],
        check=True,capture_output=True,text=True)
    record={"machine_label":os.environ.get("RUNNER_NAME",platform.node()),
        "os":platform.platform(),"python":platform.python_version(),
        "cpu":platform.processor(),"benchmark":json.loads((output/"paired.json").read_text()),
        "stdout_tail":result.stdout[-2000:]}
    (output/"reproduction.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
