"""Đọc cấu hình pipeline và schema nguồn từ conf/ (FR-03).

Mọi tên cột, đường dẫn và dải kỳ nạp lấy từ đây. Code chỉ biết hai vai trò cột: khóa khoản vay
(loan_key) và tháng báo cáo (reporting_period), được đánh dấu bằng `role:` trong conf/schema/*.yml.
"""
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import yaml

DEFAULT_CONF_DIR = Path(__file__).resolve().parent.parent / "conf"


@dataclass(frozen=True)
class Column:
    pos: int
    name: str
    type: str
    role: str | None = None
    # Khai báo gốc trong conf/schema (missing, domain, values, pattern, nullable...), dùng cho cổng chất lượng
    spec: dict = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class SourceSchema:
    """Schema một loại file nguồn (orig hoặc perf) theo File Layout."""

    kind: str
    field_count: int
    columns: tuple[Column, ...]
    file_pattern: dict[str, str]

    def column_with_role(self, role: str) -> str:
        matches = [c.name for c in self.columns if c.role == role]
        if len(matches) != 1:
            raise ValueError(f"conf/schema/{self.kind}.yml cần đúng một cột role: {role}, đang có {matches}")
        return matches[0]


class Config:
    def __init__(self, conf_dir: str | Path | None = None):
        self.conf_dir = Path(conf_dir or os.environ.get("LAKEHOUSE_CONF_DIR") or DEFAULT_CONF_DIR)
        self.pipeline = yaml.safe_load((self.conf_dir / "pipeline.yml").read_text())

    @property
    def source(self) -> str:
        return self.pipeline["dataset"]["source"]

    @property
    def vintage(self) -> int:
        return self.pipeline["dataset"]["vintage"]

    @property
    def record_source(self) -> str:
        return self.pipeline["dataset"]["record_source"].format(source=self.source, vintage=self.vintage)

    @property
    def raw_dir(self) -> Path:
        return Path(self.pipeline["paths"]["raw"][self.source])

    @property
    def lag_months(self) -> int:
        return self.pipeline["load_date"]["lag_months"]

    @property
    def bronze(self) -> dict:
        return self.pipeline["bronze"]

    @cached_property
    def orig(self) -> SourceSchema:
        return self._schema("orig")

    @cached_property
    def perf(self) -> SourceSchema:
        return self._schema("perf")

    def raw_files(self, schema: SourceSchema) -> str:
        """Glob các file nguồn của schema trong thư mục raw của nguồn đang chọn."""
        return str(self.raw_dir / schema.file_pattern[self.source].format(vintage=self.vintage))

    def _schema(self, kind: str) -> SourceSchema:
        raw = yaml.safe_load((self.conf_dir / "schema" / f"{kind}.yml").read_text())
        columns = tuple(Column(c["pos"], c["name"], c["type"], c.get("role"), c) for c in raw["columns"])
        positions = [c.pos for c in columns]
        if positions != list(range(1, raw["field_count"] + 1)):
            raise ValueError(f"conf/schema/{kind}.yml: vị trí cột phải liên tục 1..{raw['field_count']}")
        return SourceSchema(kind, raw["field_count"], columns, raw["file_pattern"])
