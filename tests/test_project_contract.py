from pathlib import Path

import pandas as pd


def test_expected_top_level_directories_exist():
    root = Path(__file__).resolve().parents[1]
    for name in ["config", "src", "tests", "outputs", "scripts"]:
        assert (root / name).is_dir(), f"Missing required folder: {name}"


def test_structured_config_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "config" / "config.yaml").exists()


def test_pnl_log_schema_if_present():
    root = Path(__file__).resolve().parents[1]
    pnl_log = root / "outputs" / "pnl_log.csv"
    if not pnl_log.exists():
        return

    df = pd.read_csv(pnl_log, nrows=5)
    required = {"timestamp", "realized_pnl", "unrealized_pnl"}
    assert required.issubset(df.columns)
