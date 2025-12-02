from config import HF_MODEL
from typing import Tuple

USE_TRANSFORMERS = False
MODEL = None

if HF_MODEL:
    try:
        from transformers import pipeline
        MODEL = pipeline("sentiment-analysis", model=HF_MODEL)
        USE_TRANSFORMERS = True
    except Exception as e:
        print("Не вдалося завантажити HF модель:", e)
        USE_TRANSFORMERS = False

def _simple_fallback(text: str) -> Tuple[str, float]:
    text_low = text.lower()
    good = ["добре", "радіс", "щас", "спокі", "ok", "happy"]
    bad = ["поган", "сум", "депрес", "втом", "стрес", "тривож"]
    score = 0.0
    for w in good:
        if w in text_low: score += 0.6
    for w in bad:
        if w in text_low: score -= 0.6
    if score > 0.2: return "positive", min(1.0, score)
    if score < -0.2: return "negative", max(0.0, -score)
    return "neutral", 0.5

def analyze_text(text: str) -> Tuple[str, float]:
    if USE_TRANSFORMERS and MODEL:
        try:
            res = MODEL(text[:1000])
            r = res[0]
            label = r.get("label", "").lower()
            score = float(r.get("score", 0.0))
            if "pos" in label: label = "positive"
            elif "neg" in label: label = "negative"
            else: label = "neutral"
            return label, score
        except Exception:
            return _simple_fallback(text)
    else:
        return _simple_fallback(text)
