# Benchmark protocol

Run: python benchmarks/run_benchmarks.py --events 10000 --warmups 2 --repeats 7

The harness performs warmups excluded from measurement, records each repetition using time.perf_counter, and reports minimum, median, mean, maximum, and median throughput. The JSON result includes the experiment manifest, runtime/platform, workload parameters, raw samples, and methodology.

For defensible comparisons:

1. Pin the Chronos commit, Python version, OS, CPU, power mode, and dependencies.
2. Use identical event counts, timestamp distributions, payload shapes, warmups, and repetitions.
3. Alternate scheduler run order to reduce thermal and background-load bias.
4. Publish raw samples, not only best-case numbers; report median and spread.
5. Separate scheduler cost from payload handling, serialization, replay, and I/O.
6. Repeat on multiple machines before generalizing.

The included sorted-list implementation is a simple reference baseline, not a third-party simulator. This microbenchmark does not provide statistical significance analysis.
