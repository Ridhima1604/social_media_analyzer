import re
from datetime import datetime
from zoneinfo import ZoneInfo
from transformers import pipeline   # ✅ import pipeline

# Load Hugging Face models
sentiment_pipe = pipeline("sentiment-analysis")
paraphrase_pipe = pipeline("text2text-generation", model="Vamsi/T5_Paraphrase_Paws")

POSITIVE_BOOST_WORDS = ["amazing", "exciting", "exclusive", "limited", "join"]

def extract_entities(text: str):
    hashtags = re.findall(r"#(\w+)", text)
    mentions = re.findall(r"@(\w+)", text)
    urls = re.findall(r"(https?://\S+)", text)
    return {"hashtags": hashtags, "mentions": mentions, "urls": urls}

def analyze_sentiment(text: str):
    res = sentiment_pipe(text[:512])[0]
    label = res["label"].lower()
    score = float(res["score"])
    compound = score if label == "positive" else -score
    return {"label": label, "score": score, "compound": compound}

def suggest_best_times(tz: str = "Asia/Kolkata"):
    return {
        "weekday": ["08:00", "12:30", "18:00", "21:00"],
        "weekend": ["10:00", "14:00", "19:00", "21:30"],
        "now_local": datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")
    }

def generate_paraphrases(text: str, num: int = 3):
    prompt = f"paraphrase: {text}"
    outs = paraphrase_pipe(
        prompt,
        num_return_sequences=num,
        do_sample=True,
        top_p=0.92,
        top_k=50
    )
    cands = [o["generated_text"].strip().replace("\n", " ") for o in outs]
    seen, unique = set(), []
    for c in cands:
        if c.lower() not in seen:
            unique.append(c)
            seen.add(c.lower())
    return unique

def improvement_suggestions(text: str, sentiment: dict, entities: dict):
    suggestions = []
    word_count = len(text.split())

    if sentiment["compound"] < 0:
        suggestions.append("Tone feels negative; consider a more upbeat phrasing.")

    if word_count < 8:
        suggestions.append("Caption is very short; add context or a call-to-action.")
    elif word_count > 40:
        suggestions.append("Caption is long; tighten to improve skim-readability.")

    if len(entities.get("hashtags", [])) < 2:
        suggestions.append("Add 2–3 specific hashtags; avoid overly generic ones.")

    if not any(w in text.lower() for w in ["link in bio", "read more", "check out", "learn more", "join", "register"]):
        suggestions.append("Include a clear call-to-action (e.g., ‘Learn more’, ‘Join us today’).")

    missing = [w for w in POSITIVE_BOOST_WORDS if w not in text.lower()]
    if missing:
        suggestions.append("Consider using engaging keywords like: " + ", ".join(missing[:4]) + ".")

    return suggestions   # ✅ fixed
