"""Lightweight BM25 scorer with zero external dependencies.

Tokenization (§: query/P2 decision — zero-dep bigram):
  * ASCII runs (a-z0-9) lower-cased as whole tokens.
  * CJK runs split into character **bigrams** (better recall than unigram for
    short queries, still deterministic and dependency-free).
"""

from __future__ import annotations

import math
import re
from collections import Counter

_CJK_RE = re.compile(r"[一-鿿]+")
_ASCII_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens: list[str] = list(_ASCII_RE.findall(text))
    for seg in _CJK_RE.findall(text):
        for i in range(len(seg) - 1):
            tokens.append(seg[i : i + 2])
        if len(seg) == 1:  # single CJK char still indexable
            tokens.append(seg)
    return tokens


class BM25:
    """Classic BM25 over an in-memory corpus. Deterministic, no deps."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.n = len(docs)
        self.df: dict[str, int] = Counter()
        for d in docs:
            for t in set(d):
                self.df[t] += 1
        self.avgdl = (sum(len(d) for d in docs) / self.n) if self.n else 0.0
        self.idf = {
            t: math.log(1.0 + (self.n - df + 0.5) / (df + 0.5))
            for t, df in self.df.items()
        }

    def score(self, query: list[str], doc_idx: int) -> float:
        dl = len(self.docs[doc_idx])
        if dl == 0 or self.avgdl == 0:
            return 0.0
        tf = Counter(self.docs[doc_idx])
        total = 0.0
        for t in query:
            f = tf.get(t, 0)
            if f == 0 or t not in self.idf:
                continue
            denom = f + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
            total += self.idf[t] * (f * (self.k1 + 1.0)) / denom
        return total
