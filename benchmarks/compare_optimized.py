"""Compare per-request CLI Piper with a persistent in-process model."""
import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from voice_production.core import Pipeline, inspect_audio
from voice_production.neural import PiperEngine
from voice_production.persistent_neural import PersistentPiperEngine

TEXTS = [
 "The quiet harbor shimmered under moonlight as the ferry approached the island.",
 "Beyond the cedar forest, the travelers discovered a forgotten stone bridge.",
 "The archivist opened the letter and recognized her grandfather’s handwriting.",
 "Before sunrise, a chorus of birds welcomed the first visitors to the valley.",
 "At the station, the announcer called the final train departing for the coast.",
 "The inventor explained her curious machine to an audience of young students.",
 "Rain swept across the old library roof while the detective searched the shelves.",
 "After the storm passed, the captain recorded the voyage in the ship’s journal.",
 "For a moment, the crowded city seemed perfectly still beneath the falling snow.",
 "The final chapter ended with a promise to return before the next spring.",
]

def percentile(values, pct):
    ordered = sorted(values)
    position = (len(ordered) - 1) * pct / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)

def run_engine(name, factory, count, root):
    begin = time.perf_counter()
    engine = factory()
    initialization = time.perf_counter() - begin
    pipeline = Pipeline(root / name, neural_engine=engine)
    ids = [pipeline.enqueue("benchmark", TEXTS[i % len(TEXTS)]) for i in range(count)]
    times, completed, failures = [], [], []
    start = time.perf_counter()
    for jid in ids:
        t = time.perf_counter()
        record = pipeline.process(jid)
        times.append(time.perf_counter() - t)
        if record["status"] == "completed":
            completed.append(record)
        else:
            failures.append({"job_id": jid, "error": record["error"]})
    wall = time.perf_counter() - start
    checks = [inspect_audio(record["output"]) for record in completed]
    duration = sum(report["duration_sec"] for report in checks)
    return {
        "engine": name, "requested": count, "completed": len(completed),
        "failed": len(failures), "failure_details": failures[:5],
        "engine_init_seconds": round(initialization, 3),
        "processing_wall_seconds": round(wall, 3),
        "end_to_end_wall_seconds": round(initialization + wall, 3),
        "jobs_per_second": round(len(completed) / wall, 3) if wall else None,
        "median_job_seconds": round(statistics.median(times), 3),
        "p95_job_seconds": round(percentile(times, 95), 3),
        "total_audio_seconds": round(duration, 3),
        "real_time_factor": round(wall / duration, 3) if duration else None,
        "silence_failures": sum(int(report["silent"]) for report in checks),
        "clipping_failures": sum(int(report["clipped"]) for report in checks),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("results/piper_optimization.json"))
    parser.add_argument("--piper-bin", default="piper")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        baseline = run_engine("per_job_cli", lambda: PiperEngine(args.model.resolve(), args.piper_bin), args.jobs, root)
        persistent = run_engine("persistent_model", lambda: PersistentPiperEngine(args.model.resolve()), args.jobs, root)
    first, second = baseline["processing_wall_seconds"], persistent["processing_wall_seconds"]
    valid = baseline["completed"] == persistent["completed"] == args.jobs
    result = {
        "description": "Identical sequential text segments; each job includes WAV postprocessing and QC; CPU/environment-dependent.",
        "baseline": baseline, "persistent": persistent,
        "all_jobs_completed": valid,
        "processing_time_reduction_percent": round((first - second) / first * 100, 2) if valid and first else None,
        "processing_throughput_speedup": round(first / second, 3) if valid and second else None,
        "notes": [
            "Persistent engine loads the model once; initialization is separately reported.",
            "No perceptual naturalness or word-error-rate evaluation was performed.",
            "Repeat runs and alternate benchmark order for more reliable estimates.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("Saved:", args.output.resolve())
    return 0 if valid else 1

if __name__ == "__main__":
    raise SystemExit(main())
