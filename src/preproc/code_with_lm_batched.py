"""Minimal batch open-coding pipeline for Zendo transcripts."""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
from typing import Iterable

import openai
from tqdm import tqdm

from src.preproc.prompts import get_open_coding_prompt


def parse_scene_pid(name: str) -> tuple[str, str]:
    parts = name.split("_")
    pid = next((p for p in parts if p.startswith("p")), name)
    scene = next((p for p in parts if p.startswith("scene")), "scene")
    return scene, pid


def call_model(client: openai.Client, prompt: str, text: str, model: str) -> list:
    msgs = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]
    resp = client.chat.completions.create(
        model=model,
        messages=msgs,
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        logging.warning("Failed to parse JSON from model output", exc_info=True)
        return []


def process_file(
    client: openai.Client,
    prompt: str,
    txt_path: pathlib.Path,
    out_dir: pathlib.Path,
    model: str,
) -> pathlib.Path:
    text = txt_path.read_text(encoding="utf-8")
    records = call_model(client, prompt, text, model)
    scene, pid = parse_scene_pid(txt_path.stem)
    out_path = out_dir / f"{scene}_{pid}.jsonl"
    with out_path.open("w", encoding="utf-8") as out_f:
        for record in records:
            out_f.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
            out_f.write("\n") 
    return out_path


def main(argv: Iterable[str] | None = None) -> None:

    parser = argparse.ArgumentParser()
    parser.add_argument("--in_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--model_name", default="gpt-4")
    args = parser.parse_args(argv)

    in_root = pathlib.Path(args.in_dir)
    if in_root.is_file():
        files = [in_root]
    else:
        files = sorted(in_root.glob("*.txt"))
    out_root = pathlib.Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    prompt = get_open_coding_prompt()
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

    logging.info(f"Found {len(files)} transcript(s) in {in_root}")

    for txt_file in tqdm(files, desc="Open‐coding transcripts"):
        try:
            out_path = process_file(client, prompt, txt_file, out_root, args.model_name)
            logging.info(f"Wrote codes for {txt_file.name} → {out_path.name}")
        except Exception:
            logging.error(f"Error processing {txt_file.name}", exc_info=True)

    logging.info("All done.")


if __name__ == "__main__":
    main()
