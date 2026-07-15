# preprocess.py
# Robust preprocessing for tmdb_5000 + Kaggle Books
import pandas as pd
import ast
import os

def infer_mood(text):
    text = text.lower()

    if any(w in text for w in ["comedy", "fun", "family", "friendship", "joy"]):
        return "happy"

    if any(w in text for w in ["romance", "love", "heart", "relationship"]):
        return "relaxed"

    if any(w in text for w in ["success", "biography", "entrepreneur", "business"]):
        return "motivated"

    if any(w in text for w in ["war", "crime", "thriller", "mystery"]):
        return "excited"

    if any(w in text for w in ["sad", "death", "loss", "tragedy"]):
        return "sad"

    return "neutral"

def infer_goal(text):
    text = text.lower()

    if any(w in text for w in ["english", "language", "grammar", "vocabulary"]):
        return "improve english"

    if any(w in text for w in ["business", "finance", "entrepreneur"]):
        return "learn business"

    if any(w in text for w in ["history", "war", "ancient"]):
        return "learn history"

    if any(w in text for w in ["art", "design", "creative", "fiction"]):
        return "improve creativity"

    if any(w in text for w in ["motivation", "success", "mindset"]):
        return "be motivated"

    return "general"

print("Reading TMDB files...")

movie_folder = os.path.join(".", "movie_raw_data")
book_folder = os.path.join(".", "books_raw_data")

movies_path = os.path.join(movie_folder, "tmdb_5000_movies.csv")
credits_path = os.path.join(movie_folder, "tmdb_5000_credits.csv")

if not os.path.exists(movies_path):
    raise FileNotFoundError(f"{movies_path} not found.")
if not os.path.exists(credits_path):
    raise FileNotFoundError(f"{credits_path} not found.")

movies_df = pd.read_csv(movies_path, low_memory=False)
credits_df = pd.read_csv(credits_path, low_memory=False)

print("Movie columns:", list(movies_df.columns))
print("Credits columns:", list(credits_df.columns))

# Ensure numeric ids
movies_df["id"] = pd.to_numeric(movies_df["id"], errors="coerce")
credits_df["movie_id"] = pd.to_numeric(credits_df["movie_id"], errors="coerce")

# Rename credits title to avoid collision with movies' title column
if "title" in credits_df.columns:
    credits_df = credits_df.rename(columns={"title": "credits_title"})

# Merge on id/movie_id (left = movies)
merged = movies_df.merge(credits_df, left_on="id", right_on="movie_id", how="left")

# Helper to safely parse JSON-like strings
def safe_eval_list(text):
    if pd.isna(text):
        return []
    try:
        return ast.literal_eval(text)
    except Exception:
        try:
            return eval(text)
        except Exception:
            return []

def extract_names_from_list(text, key="name", limit=None):
    items = safe_eval_list(text)
    names = []
    for it in items:
        if isinstance(it, dict):
            val = it.get(key, "")
            if val:
                names.append(str(val).strip())
        else:
            names.append(str(it).strip())
    if limit:
        names = names[:limit]
    return " | ".join([n for n in names if n])

def extract_director(crew_text):
    items = safe_eval_list(crew_text)
    for it in items:
        if isinstance(it, dict):
            job = str(it.get("job","")).lower()
            if job == "director":
                return it.get("name","")
    return ""

def parse_genres(genre_text):
    items = safe_eval_list(genre_text)
    names = []
    for it in items:
        if isinstance(it, dict):
            names.append(str(it.get("name","")).strip())
        else:
            names.append(str(it).strip())
    return " | ".join([n for n in names if n])

# Build fields
print("Extracting fields...")

# title from movies_df should still be present as 'title' (no collision now)
if "title" not in merged.columns and "original_title" in merged.columns:
    merged["title"] = merged["original_title"].astype(str)
elif "title" not in merged.columns:
    # fallback: try title_x or first available title-like column
    for c in ["title_x", "title_y", "original_title"]:
        if c in merged.columns:
            merged["title"] = merged[c].astype(str)
            break

merged["genre"] = merged.get("genres", "").apply(lambda x: parse_genres(x) if x is not None else "")
# cast comes from credits_df 'cast' column (stringified list)
merged["cast"] = merged.get("cast", "").apply(lambda x: extract_names_from_list(x, key="name", limit=5) if x is not None else "")
# director from crew column
merged["director"] = merged.get("crew", "").apply(lambda x: extract_director(x) if x is not None else "")
# story_tags — use overview text
merged["story_tags"] = merged.get("overview", "").fillna("").astype(str).str.replace("\n"," ").str.strip()
# -------- AUTO MOOD & GOAL TAGS (derived) --------
def infer_mood(text):
    t = text.lower()
    if any(w in t for w in ["happy","fun","joy","love","comedy","friendship"]):
        return "happy"
    if any(w in t for w in ["dark","revenge","crime","war","death","sad"]):
        return "sad"
    if any(w in t for w in ["hero","fight","battle","action","adventure"]):
        return "excited"
    return "neutral"

def infer_goal(text):
    t = text.lower()
    if any(w in t for w in ["motivation","success","dream","goal","inspire"]):
        return "self growth"
    if any(w in t for w in ["love","relationship","family"]):
        return "relationships"
    if any(w in t for w in ["escape","fantasy","magic","adventure"]):
        return "entertainment"
    return "general"

merged["mood_tag"] = merged["story_tags"].apply(infer_mood)
merged["goal_tag"] = merged["story_tags"].apply(infer_goal)

# poster_url: tmdb poster path -> build full URL if present
def make_poster_url(p):
    if pd.isna(p) or str(p).strip()=="":
        return ""
    p = str(p).strip()
    if p.startswith("http"):
        return p
    return f"https://image.tmdb.org/t/p/w500{p}"

# try several poster-like columns
poster_col = None
for c in ["poster_path","poster","image","backdrop_path","homepage"]:
    if c in merged.columns:
        poster_col = c
        break

if poster_col:
    merged["poster_url"] = merged[poster_col].apply(make_poster_url)
else:
    merged["poster_url"] = ""

# Select and save
movies_out = merged[["title","genre","cast","director","story_tags","mood_tag","goal_tag","poster_url"]].drop_duplicates(subset=["title"])
movies_out.to_csv("movies.csv", index=False, encoding="utf-8-sig")
print(f"Saved movies.csv with {len(movies_out)} rows.")

# =========================
# BOOKS PREPROCESSING
# =========================

print("Processing books...")

books = pd.read_csv(
    "./books_raw_data/Books.csv",
    encoding="latin-1",
    sep=";",
    engine="python",
    on_bad_lines="skip"
)

books.columns = books.columns.str.strip()

books["text_for_analysis"] = (
    books["Book-Title"].astype(str) + " " +
    books["Book-Author"].astype(str) + " " +
    books["Publisher"].astype(str)
)

# 🔹 Infer mood & goal from REAL description
books["mood_tag"] = books["text_for_analysis"].apply(infer_mood)
books["goal_tag"] = books["text_for_analysis"].apply(infer_goal)

# Clean output
books_clean = pd.DataFrame({
    "title": books["Book-Title"].astype(str).str.strip(),
    "author": books["Book-Author"].astype(str).str.strip(),
    "description": books["text_for_analysis"],
    "mood_tag": books["mood_tag"],
    "goal_tag": books["goal_tag"],
    "cover_url": books["Image-URL-L"].fillna("")
})

books_clean.to_csv("books.csv", index=False, encoding="utf-8-sig")
print("books.csv created successfully with mood & goal tags")

