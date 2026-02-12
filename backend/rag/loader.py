from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str
    metadata: dict


def _infer_app_name(path: Path, text: str) -> str:
    if text:
        first_line = text.strip().splitlines()[0].strip()
        if first_line.startswith("#"):
            return first_line.lstrip("#").strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def load_markdown_documents(source_dir: str | Path) -> List[Document]:
    base = Path(source_dir)
    documents: List[Document] = []
    for path in sorted(base.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        app_name = _infer_app_name(path, text)
        documents.append(
            Document(
                doc_id=path.relative_to(base).as_posix(),
                text=text,
                metadata={
                    "app": app_name,
                    "source_path": path.as_posix(),
                },
            )
        )
    return documents


def iter_documents(source_dir: str | Path) -> Iterable[Document]:
    return load_markdown_documents(source_dir)
