"""The governed source documents a response is checked against.

There is often no real-time ground truth for an arbitrary claim -- the brief
says so explicitly. What an enterprise *does* have is a set of documents it
has agreed to be bound by. We verify against those, and say "unsupported"
rather than "false" when we cannot find backing evidence.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_LIST_MARKER = re.compile(r"^\s*(?:\d+\.|[-*])\s*")


def split_sentences(text: str) -> list[str]:
    out = []
    for chunk in _SENT_SPLIT.split(text or ""):
        chunk = _LIST_MARKER.sub("", chunk)
        chunk = " ".join(chunk.split())
        if len(chunk) > 12 and not chunk.startswith("#"):
            out.append(chunk)
    return out


@dataclass
class Corpus:
    use_case: str
    docs: dict[str, str] = field(default_factory=dict)
    sentences: list[str] = field(default_factory=list)
    sentence_doc: list[str] = field(default_factory=list)
    _doc_nums: dict = field(default_factory=dict)
    _vec: TfidfVectorizer | None = None
    _matrix: object = None

    def build(self) -> "Corpus":
        # Word + character n-grams: character n-grams keep the match robust to
        # the paraphrasing a model does, which pure word overlap misses.
        self._vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1
        )
        self._matrix = self._vec.fit_transform(self.sentences or [""])
        return self

    def doc_numbers(self, doc_id: str) -> set:
        """Figures asserted by one source document.

        Grounding is scoped to the document a claim actually matches. A
        shipping SLA of 3-5 days must not be allowed to vouch for a refund
        window of 5 days just because both numbers exist somewhere in the
        corpus.
        """
        from controlplane.slowlane.judge import numbers

        if doc_id not in self._doc_nums:
            self._doc_nums[doc_id] = numbers(self.docs.get(doc_id, ""))
        return self._doc_nums[doc_id]

    @property
    def all_text(self) -> str:
        return "\n".join(self.docs.values())

    def best_match(self, claim: str) -> tuple[float, str, str]:
        """Return (similarity, sentence, doc_id) for the best supporting line."""
        if self._vec is None:
            self.build()
        if not self.sentences:
            return 0.0, "", ""
        q = self._vec.transform([claim])
        sims = (self._matrix @ q.T).toarray().ravel()
        i = int(np.argmax(sims))
        return float(sims[i]), self.sentences[i], self.sentence_doc[i]

    def top_matches(self, claim: str, k: int = 3) -> list[tuple[float, str, str]]:
        if self._vec is None:
            self.build()
        if not self.sentences:
            return []
        q = self._vec.transform([claim])
        sims = (self._matrix @ q.T).toarray().ravel()
        idx = np.argsort(-sims)[:k]
        return [(float(sims[i]), self.sentences[i], self.sentence_doc[i]) for i in idx]


@functools.lru_cache(maxsize=8)
def load_corpus(use_case: str) -> Corpus:
    c = Corpus(use_case=use_case)
    d = CORPUS_DIR / use_case
    if d.exists():
        for f in sorted(d.glob("*.md")):
            text = f.read_text()
            c.docs[f.name] = text
            for s in split_sentences(text):
                c.sentences.append(s)
                c.sentence_doc.append(f.name)
    return c.build()
