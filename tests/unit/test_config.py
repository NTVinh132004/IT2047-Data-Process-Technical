import shutil

import pytest
import yaml

from ingestion.config import Config
from ingestion.periods import periods_between


def test_schema_matches_release_47():
    cfg = Config()
    assert cfg.orig.field_count == 31 and len(cfg.orig.columns) == 31
    assert cfg.perf.field_count == 35 and len(cfg.perf.columns) == 35
    assert cfg.orig.column_with_role("loan_key") == "loan_id"
    assert cfg.perf.column_with_role("reporting_period") == "reporting_period"


def test_raw_files_follow_source(tmp_path):
    shutil.copytree(Config().conf_dir, tmp_path / "conf")
    cfg = Config(tmp_path / "conf")
    assert cfg.raw_files(cfg.perf) == "/data/raw/sample_2019/sample_perf_2019.txt"
    pipeline = yaml.safe_load((tmp_path / "conf/pipeline.yml").read_text())
    pipeline["dataset"]["source"] = "historical"
    (tmp_path / "conf/pipeline.yml").write_text(yaml.safe_dump(pipeline))
    cfg = Config(tmp_path / "conf")
    assert cfg.raw_files(cfg.orig) == "/data/raw/historical_2019/orig_2019Q?.txt"
    assert cfg.record_source == "freddiemac.sflld.historical_2019"


def test_positions_must_be_contiguous(tmp_path):
    shutil.copytree(Config().conf_dir, tmp_path / "conf")
    schema_file = tmp_path / "conf/schema/perf.yml"
    schema = yaml.safe_load(schema_file.read_text())
    schema["columns"][5]["pos"] = 99
    schema_file.write_text(yaml.safe_dump(schema))
    with pytest.raises(ValueError, match="liên tục"):
        Config(tmp_path / "conf").perf


def test_periods_between():
    assert periods_between("2019Q3", "2020Q2") == ["2019Q3", "2019Q4", "2020Q1", "2020Q2"]
    assert len(periods_between("2019Q1", "2026Q1")) == 29
