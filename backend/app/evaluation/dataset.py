from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class QAItem:
    question: str
    ground_truth_answer: str
    source_file: str


def load_qa_dataset(path: str) -> List[QAItem]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Eval dataset not found at {path}. See app/evaluation/qa_dataset.json for the format "
            "(question, ground_truth_answer, source_file)."
        )
    with open(p, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [QAItem(**item) for item in raw]
