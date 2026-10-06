"""Inference: resume text -> {"SKILLS": [...], "DEGREE": [...], ...} with the fine-tuned model.

Needs torch + transformers (installed in Colab; install them locally before using the model
in the Django backend). NOT yet run against a trained model - do that after notebook 03.
"""

import json
import os

import data


class ResumeNER:
    def __init__(self, model_dir: str, chunk_size: int = 150, stride: int = 100):
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForTokenClassification.from_pretrained(model_dir).eval()
        with open(os.path.join(model_dir, "labels.json"), "r", encoding="utf-8") as f:
            self.labels = json.load(f)
        self.chunk_size, self.stride = chunk_size, stride

    def tag_words(self, words: list) -> list:
        """One BIO tag per word. Overlapping windows: the first window to cover a word wins."""
        tags = [None] * len(words)
        start = 0
        while start < len(words):
            window = words[start:start + self.chunk_size]
            enc = self.tok(window, is_split_into_words=True, truncation=True,
                           max_length=512, return_tensors="pt")
            with self.torch.no_grad():
                pred = self.model(**enc).logits.argmax(-1)[0].tolist()
            prev = None
            for pos, w in enumerate(enc.word_ids(0)):
                if w is not None and w != prev and tags[start + w] is None:
                    tags[start + w] = self.labels[pred[pos]]
                prev = w
            if start + self.chunk_size >= len(words):
                break
            start += self.stride
        return [t or "O" for t in tags]

    def extract(self, text: str) -> dict:
        words = [w for w in (data.clean_token(t) for t in text.split()) if w]
        tags = self.tag_words(words)
        out, cur_label, cur = {}, None, []
        for w, t in zip(words + [""], tags + ["O"]):
            if t.startswith("I-") and cur_label == t[2:]:
                cur.append(w)
                continue
            if cur_label:
                out.setdefault(cur_label, []).append(" ".join(cur))
            cur_label, cur = (t[2:], [w]) if t != "O" else (None, [])
        return out
