"""Generate speech and assemble a chapter with the eSpeak default engine."""
import argparse
import json
from .core import Pipeline

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="production_data")
    parser.add_argument("--chapter", default="chapter1")
    parser.add_argument("--text", default="This is an audiobook production system.")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    pipeline = Pipeline(args.directory)
    jid = pipeline.enqueue(args.chapter, args.text)
    pipeline.process_pending(args.workers)
    chapter_path = pipeline.assemble_chapter(args.chapter)
    print(json.dumps({"job": pipeline.get(jid), "chapter_audio": str(chapter_path)}, indent=2))

if __name__ == "__main__":
    main()
