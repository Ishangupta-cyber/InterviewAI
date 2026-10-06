"""Data preparation for the resume NER model (pure Python, no heavy deps).

Pipeline: DataTurks-style JSONL -> whitespace tokens + BIO tags -> clean -> dedupe
-> split -> sliding-window chunks (BERT sees at most 512 word-pieces).

Format of one input line (DataTurks "Resume Entities for NER"):
  {"content": "<full resume text>",
   "annotation": [{"label": ["Skills"], "points": [{"start": 10, "end": 41, "text": "..."}]}, ...]}
`end` is the index of the LAST character (inclusive), so the Python slice end is end + 1.
"""

import json
import random
import re
import unicodedata
from collections import Counter

TOKEN_RE = re.compile(r"\S+")
# Labels in the source data that carry no usable signal (2 stray spans in DataTurks): treated as "O".
DROP_LABELS = {"UNKNOWN"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){9,11}(?!\d)")


def load_jsonl(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def clean_token(tok: str) -> str:
    """Normalise unicode and drop control / zero-width characters. May return ''."""
    tok = unicodedata.normalize("NFKC", tok)
    return "".join(c for c in tok if unicodedata.category(c) not in ("Cc", "Cf", "Cs")).strip()


def mask_pii(text: str) -> str:
    """For resumes contributed by people (not the public dataset): hide contact details."""
    return PHONE_RE.sub("<PHONE>", EMAIL_RE.sub("<EMAIL>", text))


def _spans(record: dict) -> list:
    """[(start, end_exclusive, LABEL)] sorted by start; later overlapping spans are dropped."""
    spans = []
    for ann in record.get("annotation") or []:
        labels = ann.get("label") or []
        if not labels:
            continue
        label = labels[0].strip().upper().replace(" ", "_")
        if label in DROP_LABELS:
            continue
        for p in ann.get("points") or []:
            spans.append((p["start"], p["end"] + 1, label))
    spans.sort()
    kept, last_end = [], -1
    for s in spans:
        if s[0] >= last_end:
            kept.append(s)
            last_end = s[1]
    return kept


def record_to_bio(record: dict):
    """-> (tokens, tags). A token is inside a span if it starts within it."""
    text = record.get("content") or ""
    spans = _spans(record)
    tokens, tags, si = [], [], 0
    open_span = None
    for m in TOKEN_RE.finditer(text):
        while si < len(spans) and spans[si][1] <= m.start():
            si += 1
        tok = clean_token(m.group())
        if not tok:
            continue
        if si < len(spans) and spans[si][0] <= m.start() < spans[si][1]:
            label = spans[si][2]
            tags.append(("I-" if open_span == si else "B-") + label)
            open_span = si
        else:
            tags.append("O")
            open_span = None
        tokens.append(tok)
    return tokens, tags


def build_examples(records: list) -> list:
    out = []
    for r in records:
        toks, tags = record_to_bio(r)
        if toks:
            out.append({"tokens": toks, "tags": tags})
    return out


def dedupe(examples: list) -> list:
    """Drop exact duplicate resumes (public datasets repeat the same resume)."""
    seen, out = set(), []
    for ex in examples:
        key = " ".join(ex["tokens"]).lower()
        if key not in seen:
            seen.add(key)
            out.append(ex)
    return out


def split(examples: list, seed: int = 42, ratios=(0.8, 0.1, 0.1)):
    """Split by RESUME (before chunking) so no resume leaks across train/val/test."""
    ex = examples[:]
    random.Random(seed).shuffle(ex)
    n = len(ex)
    a, b = int(n * ratios[0]), int(n * (ratios[0] + ratios[1]))
    return ex[:a], ex[a:b], ex[b:]


def chunk(example: dict, size: int = 200, stride: int = 150) -> list:
    """Sliding windows of `size` words; consecutive windows overlap by size - stride."""
    toks, tags = example["tokens"], example["tags"]
    if len(toks) <= size:
        return [example]
    out, i = [], 0
    while True:
        out.append({"tokens": toks[i:i + size], "tags": tags[i:i + size]})
        if i + size >= len(toks):
            break
        i += stride
    return out


def chunk_all(examples: list, size: int = 200, stride: int = 150) -> list:
    return [c for ex in examples for c in chunk(ex, size, stride)]


def label_list(examples: list) -> list:
    tags = sorted({t for ex in examples for t in ex["tags"] if t != "O"})
    return ["O"] + tags


def entity_counts(examples: list) -> Counter:
    return Counter(t[2:] for ex in examples for t in ex["tags"] if t.startswith("B-"))


def save_jsonl(examples: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
