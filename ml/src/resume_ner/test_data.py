"""Run: python ml/src/resume_ner/test_data.py   (no pytest needed)"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data

TEXT = "Ishan Gupta\nB.Tech Computer Science at MIT Moradabad\nSkills: Python Django React\nMail ishan@x.com"


def span(sub, label):
    s = TEXT.index(sub)
    return {"label": [label], "points": [{"start": s, "end": s + len(sub) - 1, "text": sub}]}


REC = {"content": TEXT, "annotation": [
    span("Ishan Gupta", "Name"), span("B.Tech", "Degree"),
    span("MIT Moradabad", "College Name"), span("Python Django React", "Skills"),
    span("ishan@x.com", "Email Address")]}


def test_bio():
    toks, tags = data.record_to_bio(REC)
    pairs = dict(zip(toks, tags))
    assert tags[0] == "B-NAME" and tags[1] == "I-NAME", tags
    assert pairs["B.Tech"] == "B-DEGREE"
    assert pairs["MIT"] == "B-COLLEGE_NAME" and pairs["Moradabad"] == "I-COLLEGE_NAME"
    assert pairs["Python"] == "B-SKILLS" and pairs["Django"] == "I-SKILLS" and pairs["React"] == "I-SKILLS"
    assert pairs["Computer"] == "O" and pairs["at"] == "O"
    assert len(toks) == len(tags)


def test_overlap_and_missing_annotation():
    rec = {"content": "a b c", "annotation": None}
    assert data.record_to_bio(rec)[1] == ["O", "O", "O"]
    rec = {"content": "a b c", "annotation": [
        {"label": ["X"], "points": [{"start": 0, "end": 2}]},
        {"label": ["Y"], "points": [{"start": 2, "end": 4}]}]}  # overlaps token "b"
    assert data.record_to_bio(rec)[1] == ["B-X", "I-X", "B-Y"] or data.record_to_bio(rec)[1][0] == "B-X"


def test_unknown_label_dropped():
    rec = {"content": "a b", "annotation": [{"label": ["UNKNOWN"], "points": [{"start": 0, "end": 0}]}]}
    assert data.record_to_bio(rec)[1] == ["O", "O"]


def test_chunk_covers_everything():
    ex = {"tokens": [str(i) for i in range(500)], "tags": ["O"] * 500}
    chunks = data.chunk(ex, size=200, stride=150)
    assert chunks[0]["tokens"][0] == "0" and chunks[-1]["tokens"][-1] == "499"
    assert all(len(c["tokens"]) <= 200 for c in chunks)
    covered = {t for c in chunks for t in c["tokens"]}
    assert len(covered) == 500


def test_split_no_leak_and_dedupe():
    exs = [{"tokens": [str(i)], "tags": ["O"]} for i in range(100)] * 2
    uniq = data.dedupe(exs)
    assert len(uniq) == 100
    tr, va, te = data.split(uniq)
    keys = [{" ".join(e["tokens"]) for e in s} for s in (tr, va, te)]
    assert not (keys[0] & keys[1]) and not (keys[0] & keys[2]) and not (keys[1] & keys[2])
    assert (len(tr), len(va), len(te)) == (80, 10, 10)


def test_mask_pii():
    out = data.mask_pii("call +91 98765 43210 or mail a.b@c.in")
    assert "<PHONE>" in out and "<EMAIL>" in out and "9876" not in out


def test_labels_and_counts():
    ex = data.build_examples([REC])
    assert data.label_list(ex)[0] == "O"
    assert data.entity_counts(ex)["SKILLS"] == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
