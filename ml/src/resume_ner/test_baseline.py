"""Run: python ml/src/resume_ner/test_baseline.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baseline


def test_shape():
    assert baseline.shape("Python3") == "Xxxd"   # X + xxxxx (runs of 3+ collapse to 2) + d
    assert baseline.shape("2023") == "dd"
    assert baseline.shape("ABC") == "XX"


def test_features_edges_and_context():
    toks = ["Ishan", "Gupta", "B.Tech"]
    f0 = baseline.word_features(toks, 0)
    assert f0["-1:edge"] and f0["1:w"] == "gupta" and f0["title"]
    f2 = baseline.word_features(toks, 2)
    assert f2["2:edge"] and f2["-1:w"] == "gupta"
    assert baseline.word_features(["2023"], 0)["year"]
    assert baseline.word_features(["a@b.com"], 0)["has_at"]


def test_fix_bio():
    assert baseline.fix_bio(["O", "I-A", "I-A", "B-B", "I-A"]) == ["O", "B-A", "I-A", "B-B", "B-A"]
    assert baseline.fix_bio(["B-A", "I-A"]) == ["B-A", "I-A"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
