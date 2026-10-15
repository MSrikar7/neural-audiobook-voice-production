"""Local speech production pipeline: SQLite job status, WAV synthesis, QC and assembly."""
import array
import re
import sqlite3
import subprocess
import sys
import time
import uuid
import wave
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

DB_SQL = """CREATE TABLE IF NOT EXISTS jobs (
id TEXT PRIMARY KEY, chapter TEXT NOT NULL, text TEXT NOT NULL,
status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
output TEXT, error TEXT, duration_sec REAL,
created REAL NOT NULL, updated REAL NOT NULL);"""

class Pipeline:
    def __init__(self, directory, neural_engine=None):
        self.neural_engine = neural_engine
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.audio = self.root / "audio"
        self.audio.mkdir(exist_ok=True)
        self.db = self.root / "jobs.db"
        self.lock = Lock()
        with self.connect() as conn:
            conn.execute(DB_SQL)

    def connect(self):
        return sqlite3.connect(self.db, timeout=30)

    def enqueue(self, chapter, text):
        if not text.strip() or len(text) > 10000:
            raise ValueError("text must contain 1-10000 characters")
        jid = uuid.uuid4().hex
        now = time.time()
        with self.lock, self.connect() as conn:
            conn.execute("INSERT INTO jobs(id,chapter,text,status,created,updated) VALUES (?,?,?,?,?,?)",
                         (jid, chapter, text, "pending", now, now))
        return jid

    def get(self, jid):
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            record = conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        return dict(record) if record else None

    def process(self, jid, voice="en", speed=165):
        job = self.get(jid)
        if not job:
            raise KeyError(jid)
        if job["status"] == "completed":
            return job
        with self.lock, self.connect() as conn:
            conn.execute("UPDATE jobs SET status='processing',attempts=attempts+1,updated=? WHERE id=?",
                         (time.time(), jid))
        raw = self.audio / f"{jid}.raw.wav"
        output = self.audio / f"{jid}.wav"
        try:
            if self.neural_engine is None:
                subprocess.run(["espeak", "-v", voice, "-s", str(speed), "-w", str(raw), job["text"]],
                               check=True, capture_output=True, timeout=60)
            else:
                self.neural_engine.synthesize(job["text"], raw)
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(raw), "-af",
                            "highpass=f=80,lowpass=f=7600,loudnorm=I=-19:TP=-3:LRA=11",
                            "-ar", "22050", "-ac", "1", str(output)],
                           check=True, capture_output=True, timeout=60)
            raw.unlink(missing_ok=True)
            report = inspect_audio(output)
            if report["duration_sec"] <= 0 or report["silent"] or report["clipped"]:
                raise RuntimeError(f"audio QC failed: {report}")
            with self.lock, self.connect() as conn:
                conn.execute("UPDATE jobs SET status='completed',output=?,duration_sec=?,error=NULL,updated=? WHERE id=?",
                             (str(output), report["duration_sec"], time.time(), jid))
        except Exception as exc:
            with self.lock, self.connect() as conn:
                conn.execute("UPDATE jobs SET status='failed',error=?,updated=? WHERE id=?",
                             (str(exc)[:400], time.time(), jid))
        return self.get(jid)

    def process_pending(self, workers=2):
        with self.connect() as conn:
            ids = [row[0] for row in conn.execute(
                "SELECT id FROM jobs WHERE status IN ('pending','failed') ORDER BY created")]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(self.process, ids))

    def assemble_chapter(self, chapter):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT output,status FROM jobs WHERE chapter=? ORDER BY created,id",
                (chapter,)).fetchall()
        if not rows or any(status != "completed" for _, status in rows):
            raise ValueError("chapter not yet complete")
        destination = self.audio / f'chapter_{re.sub(r"[^A-Za-z0-9_-]", "_", chapter)}.wav'
        with wave.open(str(destination), "wb") as target:
            for path, _ in rows:
                with wave.open(str(path), "rb") as source:
                    if target.getnframes() == 0:
                        target.setparams(source.getparams())
                    elif source.getparams()[:3] != target.getparams()[:3]:
                        raise ValueError("incompatible audio segments")
                    target.writeframes(source.readframes(source.getnframes()))
        return destination

def inspect_audio(path):
    with wave.open(str(path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
        count = wav.getnframes()
        rate = wav.getframerate()
        width = wav.getsampwidth()
    if count == 0:
        return dict(duration_sec=0, silent=True, clipped=False, peak=0, rms=0)
    if width != 2:
        raise ValueError("expected 16-bit PCM WAV")
    values = array.array("h")
    values.frombytes(frames)
    if sys.byteorder != "little":
        values.byteswap()
    peak = max(map(abs, values))
    rms = int((sum(value * value for value in values) / len(values)) ** .5)
    return dict(duration_sec=round(count / rate, 3), silent=rms < 25,
                clipped=peak >= int((2 ** (width * 8 - 1) - 1) * .997),
                peak=peak, rms=rms, sample_rate=rate)
