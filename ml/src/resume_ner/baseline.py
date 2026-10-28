"""Classical baseline for resume NER: hand-made word features + a linear classifier.

This is the "model you can train on a laptop in a minute" step that sits between the
dictionary parser already in the app and the fine-tuned DistilBERT in notebook 02.
Each word is classified on its own from features of the word and its neighbours; a small
repair step then makes the BIO tags consistent (an I- tag must follow a tag of the same label).
"""

import re

_SHAPE_SUB = [(re.compile(r"[A-Z]"), "X"), (re.compile(r"[a-z]"), "x"), (re.compile(r"\d"), "d")]


def shape(word: str) -> str:
    s = word
    for pat, rep in _SHAPE_SUB:
        s = pat.sub(rep, s)
    return re.sub(r"(.)\1{2,}", r"\1\1", s)  # xxxxxx -> xx


def word_features(tokens: list, i: int) -> dict:
    w = tokens[i]
    lw = w.lower()
    f = {
        "bias": 1.0,
        "w": lw,
        "shape": shape(w),
        "p3": lw[:3], "s3": lw[-3:], "s2": lw[-2:],
        "title": w.istitle(), "upper": w.isupper(), "digit": w.isdigit(),
        "has_digit": any(c.isdigit() for c in w),
        "has_at": "@" in w, "has_url": "indeed.com" in lw or "http" in lw,
        "len": min(len(w), 12),
        "year": bool(re.fullmatch(r"(19|20)\d\d[,.;]?", w)),
        "punct_end": w[-1] in ",.;:",
        "pos_bucket": min(i // 15, 6),  # names, titles and contact info sit at the top
    }
    for off in (-2, -1, 1, 2):
        j = i + off
        if 0 <= j < len(tokens):
            n = tokens[j]
            f[f"{off}:w"] = n.lower()
            f[f"{off}:shape"] = shape(n)
            f[f"{off}:title"] = n.istitle()
        else:
            f[f"{off}:edge"] = True
    return f


def featurize(tokens: list) -> list:
    return [word_features(tokens, i) for i in range(len(tokens))]


def fix_bio(tags: list) -> list:
    """Make tags valid IOB2: I-X is only allowed right after B-X / I-X, else it becomes B-X."""
    out, prev = [], "O"
    for t in tags:
        if t.startswith("I-") and prev[2:] != t[2:]:
            t = "B-" + t[2:]
        out.append(t)
        prev = t
    return out
