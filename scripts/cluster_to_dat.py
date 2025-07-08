#!/usr/bin/env python
import argparse
import json
import pathlib
import glob
import pandas as pd


def load_open(folder):
    dfs = []
    for f in sorted(glob.glob(f"{folder}/*.jsonl")):
        df = pd.read_json(f, lines=True)
        dfs.append((pathlib.Path(f), df))
    return dfs


def build_mapper(codebook_path):
    cb = json.load(open(codebook_path))
    mapper = {}
    for theme in cb["themes"]:
        for oc in theme["member_codes"]:
            mapper[oc] = theme["DAT_code"]
    return mapper


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--in_dir", required=True, help="path to open-codes folder")
    p.add_argument("--out_dir", required=True, help="path to DAT output folder")
    p.add_argument("--codebook", required=True, help="path to codebook.json")
    args = p.parse_args()

    mapper = build_mapper(args.codebook)
    out_root = pathlib.Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    for fp, df in load_open(args.in_dir):
        seq = df.copy()
        seq["DAT_code"] = seq["open_code"].map(mapper).fillna("OTH")
        out_path = out_root / fp.name
        seq.to_json(out_path, orient="records", lines=True)
