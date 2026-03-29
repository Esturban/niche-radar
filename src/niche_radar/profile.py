from __future__ import annotations

from collections import Counter

from .utils import (
    DISCOVERY_SIGNAL_TOKENS,
    content_tokens,
    dedupe_preserve_order,
    informative_phrase,
    safe_mean,
    tokenize,
)

ACTION_VERBS = {
    "analyzed",
    "automated",
    "built",
    "created",
    "designed",
    "developed",
    "grew",
    "launched",
    "led",
    "managed",
    "optimized",
    "scaled",
}


def extract_profile(text: str) -> dict:
    words = content_tokens(text)
    word_counts = Counter(words)
    all_tokens = tokenize(text)
    bigrams = Counter(
        " ".join(pair)
        for pair in zip(all_tokens, all_tokens[1:])
        if all(token not in {"and", "the", "for", "with"} for token in pair)
    )
    trigrams = Counter(
        " ".join(group)
        for group in zip(all_tokens, all_tokens[1:], all_tokens[2:])
        if all(token not in {"and", "the", "for", "with"} for token in group)
    )

    raw_keywords = [term for term, _ in word_counts.most_common(60)]
    raw_phrases = [
        term
        for term, _ in (bigrams + trigrams).most_common(50)
        if informative_phrase(term)
    ]
    verbs = [token for token in words if token in ACTION_VERBS]

    phrase_keywords = [
        token
        for phrase in raw_phrases
        for token in content_tokens(phrase)
        if token in DISCOVERY_SIGNAL_TOKENS
    ]
    keywords = dedupe_preserve_order(
        [keyword for keyword in raw_keywords if len(keyword) > 2 and keyword in DISCOVERY_SIGNAL_TOKENS]
        + phrase_keywords
    )[:20]
    phrases = [
        phrase
        for phrase in raw_phrases
        if any(token in DISCOVERY_SIGNAL_TOKENS for token in content_tokens(phrase))
    ][:12]
    signals = dedupe_preserve_order(phrases[:12] + keywords)
    return {
        "keywords": keywords[:20],
        "phrases": phrases[:12],
        "verbs": dedupe_preserve_order(verbs),
        "themes": signals[:18],
        "signal_density": safe_mean(word_counts.values()) if word_counts else 0.0,
    }
