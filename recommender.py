import pandas as pd
import re

movies_df = pd.read_csv("movies.csv")
books_df = pd.read_csv("books.csv")

# ---------- helpers ----------
def clean(text):
    if pd.isna(text):
        return []
    return re.findall(r"\w+", str(text).lower())

def overlap(a, b):
    return len(set(a) & set(b))


# ================= MOVIES =================
def recommend_movies(
    selected_title,
    mode,
    target_mood=None,
    goals=None,
    top_n=10
):
    mood_map = {
        "happy": ["happy", "neutral"],
        "sad": ["sad"],
        "excited": ["happy"],
        "relaxed": ["neutral"],
        "stressed": ["sad"],
        "bored": ["neutral"],
        "tired": ["neutral"]
    }


    goal_map = {
        "improve english": ["general"],
        "be motivated": ["general"],
        "learn business": ["general"],
        "learn history": ["general"],
        "improve creativity": ["general"]
    }



    results = []

    base_row = movies_df[movies_df["title"].str.lower() == selected_title.lower()]
    base_story = clean(base_row.iloc[0]["story_tags"]) if not base_row.empty else []

    for _, row in movies_df.iterrows():
        title = row["title"]
        if title.lower() == selected_title.lower():
            continue

        score = 0
        reasons = []

        story = clean(row["story_tags"])
        mood_tag = clean(row.get("mood_tag", ""))
        goal_tag = clean(row.get("goal_tag", ""))

        # ---------- Behaviour 1 ----------
        if mode == "Mood + Goal Based Recommendation":
            if target_mood:
                mapped_moods = mood_map.get(target_mood.lower(), [])
                if any(m in mood_tag for m in mapped_moods):
                    score += 5
                    reasons.append("matches your mood")


            if goals:
                for g in goals:
                    mapped_goals = goal_map.get(g.lower(), [])
                    if any(m in goal_tag for m in mapped_goals):
                        score += 3
                        reasons.append(f"supports goal: {g}")


        # ---------- Behaviour 2 ----------
        elif mode == "Similarity Based Recommendation":
            s = overlap(base_story, story)
            score += s * 2
            if s > 0:
                reasons.append(f"{s} story similarity")

        if score > 0:
            results.append({
                "title": title,
                "poster": row.get("poster_url", ""),
                "explanation": "; ".join(reasons),
                "score": score
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]


# ================= BOOKS =================
def recommend_books(
    selected_title,
    mode,
    target_mood=None,
    goals=None,
    top_n=10
):
    mood_map = {
        "happy": ["happy", "neutral"],
        "sad": ["sad"],
        "excited": ["happy"],
        "relaxed": ["neutral"],
        "stressed": ["sad"],
        "bored": ["neutral"],
        "tired": ["neutral"]
    }



    goal_map = {
        "improve english": ["general"],
        "be motivated": ["general"],
        "learn business": ["general"],
        "learn history": ["general"],
        "improve creativity": ["general"]
    }



    results = []

    base_row = books_df[books_df["title"].str.lower() == selected_title.lower()]
    base_desc = clean(base_row.iloc[0]["description"]) if not base_row.empty else []

    for _, row in books_df.iterrows():
        title = row["title"]
        if title.lower() == selected_title.lower():
            continue

        score = 0
        reasons = []

        desc = clean(row["description"])
        mood_tag = clean(row.get("mood_tag", ""))
        goal_tag = clean(row.get("goal_tag", ""))

        if mode == "Mood + Goal Based Recommendation":
            if target_mood:
                mapped_moods = mood_map.get(target_mood.lower(), [])
                if any(m in mood_tag for m in mapped_moods):
                    score += 5
                    reasons.append("matches your mood")


            if goals:
                for g in goals:
                    mapped_goals = goal_map.get(g.lower(), [])
                    if any(m in goal_tag for m in mapped_goals):
                        score += 3
                        reasons.append(f"supports goal: {g}")

        elif mode == "Similarity Based Recommendation":
            s = overlap(base_desc, desc)
            score += s * 2
            if s > 0:
                reasons.append(f"{s} description similarity")

        if score > 0:
            results.append({
                "title": title,
                "poster": row.get("cover_url", ""),
                "explanation": "; ".join(reasons),
                "score": score
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
