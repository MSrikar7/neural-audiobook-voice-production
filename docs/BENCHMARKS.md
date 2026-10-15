# Benchmark design and interpretation

The baseline and optimized engines synthesize **identical** narration sentences in sequential order. Each run includes Piper inference, WAV generation, FFmpeg postprocessing, SQLite updates and waveform validation. Test input rotates through 10 sentences; a 20-job run repeats each twice.

- **Processing time:** wall-clock seconds from processing the first job to the final job, excluding persistent-engine initialization.
- **End-to-end time:** initialization plus processing.
- **Throughput:** successful jobs divided by processing wall seconds.
- **Median / p95:** quantiles of per-job elapsed durations, including postprocessing.
- **Real-time factor:** processing wall seconds divided by generated audio seconds; below 1 means faster than audio playback in this sequential setup.
- **Time reduction:** (baseline wall - persistent wall) / baseline wall × 100.
- **Speedup:** baseline processing wall / persistent processing wall.

Three reported local Windows runs obtained processing-time reductions of 72.88%, 73.25%, and 59.14%; their arithmetic average is **68.42%**. Corresponding per-run throughput speedups were 3.688×, 3.738×, and 2.447× (arithmetic mean **3.291×**). These are not sample-weighted pooled estimates, and their spread should be disclosed.

The `results/piper_optimization.json` file documents the third run. This comparison is not an eSpeak-versus-Piper speed claim or a test of audio naturalness. Larger input diversity, alternate test order, repeated runs with raw per-job data, CPU utilization and memory measurements would strengthen the evaluation. Do not claim cloud/production scalability from these tests.
