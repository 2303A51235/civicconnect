"""Lightweight offline text classifier for CivicConnect.
Uses transparent keyword scoring so the demo runs without external APIs or model downloads.
Replace this module with a trained scikit-learn model later if required.
"""
RULES = {
    "Roads": ["pothole", "road", "street", "crack", "asphalt", "footpath", "speed breaker"],
    "Garbage": ["garbage", "trash", "waste", "dump", "rubbish", "bin", "smell", "litter"],
    "Water Leakage": ["water", "leak", "pipeline", "pipe", "tap", "drinking water", "supply"],
    "Streetlights": ["streetlight", "street light", "lamp", "electric pole", "dark road", "light not working"],
    "Drainage": ["drain", "sewage", "sewer", "flood", "stagnant", "blocked manhole", "overflow"],
}
DEPARTMENTS = {
    "Roads": "Public Works Department",
    "Garbage": "Sanitation Department",
    "Water Leakage": "Water Department",
    "Streetlights": "Electricity Department",
    "Drainage": "Drainage Department",
    "Other": "General Services",
}

def predict_complaint(text):
    text = (text or "").lower()
    scores = {category: sum(1 for word in words if word in text) for category, words in RULES.items()}
    category = max(scores, key=scores.get) if scores and max(scores.values()) > 0 else "Other"
    urgent_terms = ["danger", "accident", "injury", "exposed wire", "burst", "contaminated", "flood", "urgent"]
    high_terms = ["large", "severe", "overflow", "continuous", "many", "school", "hospital"]
    if any(term in text for term in urgent_terms):
        priority = "Critical"
    elif any(term in text for term in high_terms):
        priority = "High"
    elif category in ("Water Leakage", "Drainage", "Streetlights"):
        priority = "Medium"
    else:
        priority = "Low"
    return {"category": category, "department": DEPARTMENTS[category], "priority": priority}
