from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpan:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    @classmethod
    def from_meta(cls, meta) -> SourceSpan:
        return cls(
            start_line=getattr(meta, "line", 1),
            start_col=getattr(meta, "column", 1),
            end_line=getattr(meta, "end_line", getattr(meta, "line", 1)),
            end_col=getattr(meta, "end_column", getattr(meta, "column", 1)),
        )

    def __str__(self) -> str:
        return f"{self.start_line}:{self.start_col}-{self.end_line}:{self.end_col}"
