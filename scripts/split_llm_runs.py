#!/usr/bin/env python3
import re
import pathlib

def split_runs(txt_path: pathlib.Path, out_dir: pathlib.Path):
    """
    Split a single raw‐outputs file into multiple per‐run .txt files.
    Each run is assumed to start on a line matching TIMESTAMP = \\d+_\\d+.
    """
    text = txt_path.read_text(encoding="utf-8")
    # Split on lines *before* a timestamp. This keeps the timestamp at the start of each chunk.
    chunks = re.split(r'(?m)(?=^\d+_\d+)', text)
    # Drop any leading empty chunk
    if chunks and not chunks[0].strip():
        chunks = chunks[1:]

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = txt_path.stem  # e.g. "task1_buffer4"

    for i, chunk in enumerate(chunks, start=1):
        # Optionally strip leading/trailing blank lines
        chunk = chunk.strip() + "\n"
        out_file = out_dir / f"{stem}_run{i:02d}.txt"
        out_file.write_text(chunk, encoding="utf-8")
        print(f"Wrote {out_file.name} ({len(chunk.splitlines())} lines)")

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Split concatenated LLM runs (timestamped) into separate .txt files"
    )
    p.add_argument(
        "--in_dir",
        required=True,
        help="Folder containing taskN_bufferX.txt files",
    )
    p.add_argument(
        "--out_dir",
        required=True,
        help="Where to put the per-run .txt files (will create subfolders per task)",
    )
    args = p.parse_args()

    in_root = pathlib.Path(args.in_dir)
    out_root = pathlib.Path(args.out_dir)

    for txt_path in sorted(in_root.glob("task*_buffer*.txt")):
        # e.g. in raw_outputs/
        task_folder = out_root / txt_path.stem  # e.g. out_dir/task1_buffer4/
        print(f"\nSplitting {txt_path.name} → {task_folder}/")
        split_runs(txt_path, task_folder)
