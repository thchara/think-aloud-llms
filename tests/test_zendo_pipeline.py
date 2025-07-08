import json
import importlib.util
import pandas as pd
from pathlib import Path

from src.preproc.prompts import get_open_coding_prompt

spec = importlib.util.spec_from_file_location(
    "cluster_to_dat", Path("scripts/cluster_to_dat.py")
)
cluster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster)


def test_get_open_coding_prompt():
    text = get_open_coding_prompt()
    assert "Zendo thematic coder" in text


def test_cluster_to_dat(tmp_path):
    codebook = {"themes": [{"DAT_code": "AAA", "member_codes": ["x"]}]}
    cb_file = tmp_path / "cb.json"
    cb_file.write_text(json.dumps(codebook))

    open_rows = [
        {"id": 1, "open_code": "x"},
        {"id": 2, "open_code": "y"},
    ]
    open_file = tmp_path / "demo.jsonl"
    with open_file.open("w") as f:
        for r in open_rows:
            f.write(json.dumps(r) + "\n")

    mapper = cluster.build_mapper(cb_file)
    assert mapper == {"x": "AAA"}

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    for fp, df in cluster.load_open(tmp_path):
        seq = df.copy()
        seq["DAT_code"] = seq["open_code"].map(mapper).fillna("OTH")
        out_path = out_dir / fp.name
        seq.to_json(out_path, orient="records", lines=True)

    df_out = pd.read_json(out_dir / "demo.jsonl", lines=True)
    assert df_out["DAT_code"].tolist() == ["AAA", "OTH"]
