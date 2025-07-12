#!/usr/bin/env python
"""
Cluster open-codes → DAT codes and emit *minimal* per-run sequences
Author: 2025-07-10
"""
from __future__ import annotations
import argparse, json, re, warnings
from pathlib import Path
from typing import Iterator

import pandas as pd
from rapidfuzz import fuzz, process


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
_BLOCK_RE = re.compile(r"\n\s*\n", flags=re.MULTILINE)  # ≥1 blank line


# loader.py  (import this in cluster_to_dat.py)
import json, re, warnings
from pathlib import Path
import pandas as pd

_BLOCK_RE   = re.compile(r"\n\s*\n+")          # ≥2 blank lines
_ALT_KEYS   = {"step_id": "id",
               "code": "open_code", "openCode": "open_code"}

def load_open(folder: Path):
    """
    Yield (filepath, DataFrame) for every usable .jsonl or .json file in *folder*.
    Handles:
      • pretty-printed JSON-L (blank-line separated)
      • glued objects (…}{…)
      • a single JSON array  [ {…}, {…}, … ]
    """
    for fp in sorted(folder.glob("*.jsonl")):
        raw = fp.read_text(encoding="utf-8").strip()
        if not raw:
            continue

        # 1)  If the file is a JSON array, try that first
        if raw.lstrip().startswith("["):
            try:
                records = json.loads(raw)
            except json.JSONDecodeError as e:
                warnings.warn(f"{fp.name}: bad JSON array – {e}")
                records = []
        else:
            # 2)  Otherwise assume JSON-Lines (pretty or glued)
            chunks = (_BLOCK_RE.split(raw)
                      if "\n\n" in raw else
                      re.split(r"}\s*\n?\s*{", raw))  # handles “}{” too
            records = []
            for ch in chunks:
                ch = ch.strip()
                if not ch:
                    continue
                # add back braces removed by the split on “}{”
                if not ch.startswith("{"):
                    ch = "{" + ch
                if not ch.endswith("}"):
                    ch = ch + "}"
                try:
                    records.append(json.loads(ch))
                except json.JSONDecodeError as e:
                    warnings.warn(f"{fp.name}: bad JSON block – {e}")

        if not records:
            warnings.warn(f"{fp.name}: no usable records – skipped")
            continue

        df = pd.DataFrame.from_records(records)
        # normalise column names
        df = df.rename(columns={k: v for k, v in _ALT_KEYS.items() if k in df})
        if not {"id", "open_code"}.issubset(df.columns):
            warnings.warn(f"{fp.name}: missing id/open_code – skipped")
            continue

        yield fp, df



def build_maps(codebook_path: Path):
    cb = json.loads(codebook_path.read_text(encoding="utf-8"))
    exact = {}
    for t in cb["themes"]:
        for oc in t["member_codes"]:
            exact[oc] = t["DAT_code"]
    return exact, set(cb["DAT_code_list"])


def map_code(
    oc: str, exact: dict[str, str], thresh: int
) -> str:  # open-code → DAT_code/OTH
    if oc in exact:
        return exact[oc]
    match, score, _ = process.extractOne(oc, exact.keys(), scorer=fuzz.QRatio)
    return exact[match] if score >= thresh else "OTH"


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Cluster open-codes → DAT sequences (minimal outputs)"
    )
    ap.add_argument("--in_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--codebook", required=True)
    ap.add_argument("--fuzzy", type=int, default=90, help="0-100 threshold")
    args = ap.parse_args()

    in_root = Path(args.in_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    exact_map, _ = build_maps(Path(args.codebook))

    seq_rows = []  # for combined CSV
    participants: dict[str, dict[str, list[str]]] = {}

    for fp, df in load_open(in_root):
        # derive run_id + scene from file-name  e.g. scene_task3_buffer2_run07.jsonl
        parts = fp.stem.split("_")
        scene = parts[1]  # taskX
        run_id = parts[3]  # runYY

        df = (
            df[["id", "open_code"]]
            .assign(DAT_code=lambda d: d["open_code"].map(
                lambda oc: map_code(oc, exact_map, args.fuzzy)
            ))
            .sort_values("id")
        )

        participants.setdefault(run_id, {})
        participants[run_id].setdefault(scene, []).extend(
            df["DAT_code"].tolist()
        )

        seq_rows.extend(
            {
                "run_id": run_id,
                "scene": scene,
                "position": int(row.id),
                "code": row.DAT_code,
            }
            for row in df.itertuples()
        )

    # combined CSV -----------------------------------------------------------------
    seq_df = pd.DataFrame(seq_rows).sort_values(["run_id", "scene", "position"])
    seq_df.to_csv(out / "participant_sequence_clean.csv", index=False)

    # participant-level JSON --------------------------------------------------------
    big = []
    for run_id, scenes in sorted(participants.items()):
        big.append(
            {
                "run_id": run_id,
                "scenes": [
                    {
                        "scene": sc,
                        "sequence": [f"{i+1}. {c}" for i, c in enumerate(seq)],
                    }
                    for sc, seq in scenes.items()
                ],
            }
        )
    (out / "participant_DAT.json").write_text(json.dumps(big, indent=2))


if __name__ == "__main__":
    main()
