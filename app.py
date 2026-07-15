# app.py — Full Streamlit app with hover overlay, detail page, top-3 reasons, watchlist, TMDB trailer fetch
import streamlit as st
import pandas as pd
import os
import re
import requests
import html as html_lib
from functools import lru_cache
from db import get_db
from auth import register_user, login_user, add_to_watchlist, get_watchlist
from auth import (
    register_user,
    login_user,
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist   # ✅ REQUIRED
)

# ---------------- AFFILIATE LINK HELPERS ----------------

AMAZON_AFFILIATE_TAG = "trendypick0de-21"  # 🔁 replace with your real tag

def amazon_movie_affiliate_link(title):
    if not title:
        return None
    q = title.replace(" ", "+")
    return f"https://www.amazon.in/s?k={q}+movie&tag={AMAZON_AFFILIATE_TAG}"

def amazon_book_affiliate_link(title, author=""):
    if not title:
        return None
    q = f"{title} {author}".replace(" ", "+")
    return f"https://www.amazon.in/s?k={q}&tag={AMAZON_AFFILIATE_TAG}"


def goto_page(page):
    st.session_state.page = page
    st.session_state._page_changed = True
    st.rerun()

if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"   
if "selected_title" not in st.session_state:
    st.session_state.selected_title = ""
if "mode" not in st.session_state:
    st.session_state.mode = "Normal Similarity Recommendation"
if "content_type" not in st.session_state:
    st.session_state.content_type = "Movies"
if "last_recs" not in st.session_state:
    st.session_state.last_recs = None
if "detail_item" not in st.session_state:
    st.session_state.detail_item = None

if "search_text" not in st.session_state:
    st.session_state.search_text = ""
if "current_item" not in st.session_state:
    st.session_state.current_item = None

if "recs" not in st.session_state:
    st.session_state.recs = []

if "do_recommend" not in st.session_state:
    st.session_state.do_recommend = False
if "navigating_back" not in st.session_state:
    st.session_state.navigating_back = False
    

# -------------------------
# Optional API keys (create config.py if you want)
try:
    from config import TMDB_API_KEY, GOOGLE_BOOKS_API_KEY
except Exception:
    TMDB_API_KEY = ""
    GOOGLE_BOOKS_API_KEY = ""

# -------------------------
# Page config + style (black -> deep-red gradient) + overlay CSS
st.set_page_config(page_title="AI Recommender System", layout="wide")
# -------- Dynamic Background (Login Only) --------

if st.session_state.page == "login":
    st.markdown("""
    <style>
    .stApp {
        background: none !important;
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        z-index: -1;
        background-image: url("https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/f562aaf4-5dbb-4603-a32b-6ef6c2230136/dh0w8qv-9d8ee6b2-b41a-4681-ab9b-8a227560dc75.jpg/v1/fill/w_1192,h_670,q_70,strp/the_netflix_login_background__canada__2024___by_logofeveryt_dh0w8qv-pre.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7ImhlaWdodCI6Ijw9NzIwIiwicGF0aCI6Ii9mL2Y1NjJhYWY0LTVkYmItNDYwMy1hMzJiLTZlZjZjMjIzMDEzNi9kaDB3OHF2LTlkOGVlNmIyLWI0MWEtNDY4MS1hYjliLThhMjI3NTYwZGM3NS5qcGciLCJ3aWR0aCI6Ijw9MTI4MCJ9XV0sImF1ZCI6WyJ1cm46c2VydmljZTppbWFnZS5vcGVyYXRpb25zIl19.FScrpAAFnKqBVKwe2syeiOww6mfH6avq-DRHZ_uFVNw");
        background-size: cover;
        background-position: center bottom;
        background-repeat: no-repeat;
        opacity: 1.45;
        filter: blur(2px) saturate(90%) contrast(105%);
    }
    </style>
    """, unsafe_allow_html=True
    )

else:
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(180deg, #000000 0%, #180000 50%);
    }
    </style>
    """, unsafe_allow_html=True
    )


st.markdown("""
<style>
.affiliate-btn {
    display: inline-block;
    padding: 12px 20px;
    margin-top: 10px;
    border-radius: 10px;
    background: linear-gradient(135deg, #000000, #bfa14a);
    color: #ffd700 !important;
    font-weight: bold;
    text-decoration: none;
    box-shadow: 0 0 12px rgba(255, 215, 0, 0.6);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.affiliate-btn:hover {
    transform: translateY(-2px);
    opacity: 0.98;
    background: linear-gradient(135deg, #1a1a1a, #000000);
    box-shadow: 0 0 18px rgba(255, 215, 0, 0.9);
    box-shadow: 0 10px 26px rgba(255, 215, 0, 0.9);
}
</style>
""", unsafe_allow_html=True)


st.markdown(
    """
    <style>
    :root{
      --bg-top: #000000;
      --bg-bottom: #180000;
      --muted: #cfc5c5;
      --accent-a: #000000; /* button gradient start: black */
      --accent-b: #7a0000; /* button gradient end: deep red */
    }

    .stApp {
      background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 50%);
      color: #f7efe9;
      font-family: "Segoe UI", Roboto, Arial, sans-serif;
    }
    header { display:none; }
    .title { font-size:40px; font-weight:800; margin-bottom:6px; color:#fc0505; }
    .subtitle { color: var(--muted); margin-bottom:14px; }
    .card { background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00)); padding:16px; border-radius:12px; border: 1px solid rgba(255,255,255,0.02); margin-bottom:18px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }

    /* Buttons: black -> gold (same as affiliate buttons) */
    .stButton>button {
      display: inline-block;
      padding: 12px 18px;
      margin: 8px 8px 8px 0;
      background: linear-gradient(135deg, #000000, #2b2b2b);
      color: #FFD700 !important;
      font-weight: bold;
      border-radius: 10px;
      text-decoration: none;
      border: 1px solid #FFD700;
      box-shadow: 0 0 12px rgba(255, 215, 0, 0.6);
    }
    .stButton>button:hover {
      transform: translateY(-2px);
      opacity: 0.98;
      box-shadow: 0 0 18px rgba(255, 215, 0, 0.9);
      box-shadow: 0 10px 26px rgba(255, 215, 0, 0.9);
    }

    .rec-card { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-radius:12px; padding:12px; text-align:center; box-shadow: 0 6px 18px rgba(0,0,0,0.6); margin-bottom:10px; min-height: 360px; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; position:relative; }
    .rec-title { font-weight:800; color:#fff; margin-top:12px; }
    .rec-explain { color: var(--muted); font-size:13px; margin-top:8px; }

    /* Poster wrapper: no shimmer; images show immediately */
    .poster-wrapper { position: relative; width: 160px; height: 240px; border-radius: 6px; overflow: hidden; background: #111111; display:block; margin-bottom:8px; }
    .poster-wrapper img.poster { position: relative; width: 100%; height: 100%; object-fit: cover; display: block; opacity: 1; transition: opacity 0.15s ease-in-out; z-index: 1; }

    /* hover overlay (visual only) */
    .poster-overlay {
      position:absolute; inset:0; z-index:3; display:flex; align-items:center; justify-content:center; opacity:0; transition:opacity .18s ease;
      background: linear-gradient(180deg, rgba(0,0,0,0.0), rgba(0,0,0,0.45));
      color: #fff; font-weight:700; font-size:14px; text-align:center;
    }
    .rec-card:hover .poster-overlay { opacity:1; }

    .selected-banner { background: linear-gradient(90deg,#b22222,#7a0000); color: #ff0303; padding:12px; border-radius:10px; font-weight:700; margin-top:8px; margin-bottom:10px; }
    .css-18e3th9 { padding-top: 28px; padding-left: 28px; padding-right: 28px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def go_to(page_name):
    st.session_state.page = page_name

# Helpers: text cleaning + scoring + poster safety
def split_and_clean(s):
    if pd.isna(s) or s is None:
        return []
    if isinstance(s, (list, tuple)):
        return [str(x).strip().lower() for x in s if x]
    if isinstance(s, str):
        parts = re.split(r"\s*\|\s*|\s*;\s*|\s*,\s*", s)
        return [p.strip().lower() for p in parts if p and p.strip()!=""]
    return []
# -------------------------
# Paths & CSV loader
ROOT = "."
MOVIES_CSV = os.path.join(ROOT, "movies.csv")
BOOKS_CSV = os.path.join(ROOT, "books.csv")

def safe_load_csv(path, expected_cols=None):
    if os.path.exists(path):
        try:
            return pd.read_csv(path, low_memory=False)
        except Exception as e:
            st.warning(f"Failed to load {path}: {e}")
            return pd.DataFrame(columns=(expected_cols or []))
    else:
        return pd.DataFrame(columns=(expected_cols or []))

@st.cache_data(show_spinner=False)
def load_movies_csv():
    df = safe_load_csv(
        MOVIES_CSV,
        expected_cols=["title","genre","cast","director","story_tags","poster_url","mood_tag","goal_tag"]
    )
    df["title"] = df["title"].astype(str)
    return df


@st.cache_data(show_spinner=False)
def load_books_csv():
    df = safe_load_csv(
        BOOKS_CSV,
        expected_cols=["title","author","genre","description","language","cover_url","mood_tag","goal_tag"]
    )
    df["title"] = df["title"].astype(str)
    return df


movies_df = load_movies_csv()
books_df = load_books_csv()

@st.cache_data(show_spinner=False)
def preprocess_movies(df):
    df = df.copy()

    # Genre & cast (safe)
    if "genre" in df.columns:
        df["genre_list"] = df["genre"].fillna("").apply(split_and_clean)
    else:
        df["genre_list"] = [[]] * len(df)

    if "cast" in df.columns:
        df["cast_list"] = df["cast"].fillna("").apply(split_and_clean)
    else:
        df["cast_list"] = [[]] * len(df)

    # Mood tag (SAFE FIX)
    if "mood_tag" in df.columns:
        df["mood_tag"] = df["mood_tag"].fillna("").astype(str)
    else:
        df["mood_tag"] = ""

    # Goal tag (SAFE FIX)
    if "goal_tag" in df.columns:
        df["goal_tag"] = df["goal_tag"].fillna("").astype(str)
    else:
        df["goal_tag"] = ""

    return df

@st.cache_data(show_spinner=False)
def preprocess_books(df):
    df = df.copy()

    if "genre" in df.columns:
        df["genre_list"] = df["genre"].fillna("").apply(split_and_clean)
    else:
        df["genre_list"] = [[]] * len(df)

    if "mood_tag" in df.columns:
        df["mood_tag"] = df["mood_tag"].fillna("").astype(str)
    else:
        df["mood_tag"] = ""

    if "goal_tag" in df.columns:
        df["goal_tag"] = df["goal_tag"].fillna("").astype(str)
    else:
        df["goal_tag"] = ""

    return df



movies_df = preprocess_movies(movies_df)
books_df = preprocess_books(books_df)


# -------------------------
# Networking session + TMDB caching
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "AI-Recommender/1.0"})
SESSION_TIMEOUT = 6

@lru_cache(maxsize=1024)
def cached_tmdb_search(query):
    """Return first result object (dict) or empty dict"""
    if not TMDB_API_KEY or not query:
        return {}
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": query}
        resp = SESSION.get(url, params=params, timeout=SESSION_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if "results" in data and len(data["results"])>0:
            return data["results"][0]
        return {}
    except Exception:
        return {}
@lru_cache(maxsize=1024)
def fetch_movie_poster_tmdb(title):
    if not title:
        return ""
    try:
        res = cached_tmdb_search(title)
        p = res.get("poster_path", "") if isinstance(res, dict) else ""
        if p:
            return f"https://image.tmdb.org/t/p/w500{p}"
        return ""
    except Exception:
        return ""


@lru_cache(maxsize=1024)
def cached_tmdb_videos(movie_id):
    """Return videos list for a given TMDB movie id"""
    if not TMDB_API_KEY or not movie_id:
        return []
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
        params = {"api_key": TMDB_API_KEY}
        resp = SESSION.get(url, params=params, timeout=SESSION_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", []) or []
    except Exception:
        return []

def fetch_movie_poster_tmdb(title):
    """Return full TMDB image URL or empty string"""
    try:
        res = cached_tmdb_search(title)
        p = res.get("poster_path","") if isinstance(res, dict) else ""
        if p:
            return f"https://image.tmdb.org/t/p/w500{p}"
        return ""
    except Exception:
        return ""

def fetch_trailer_youtube(title):
    """Return YouTube watch url if found via TMDB videos (official trailer), else ''"""
    if not TMDB_API_KEY or not title:
        return ""
    try:
        res = cached_tmdb_search(title)
        movie_id = res.get("id")
        if not movie_id:
            return ""
        videos = cached_tmdb_videos(movie_id)
        # prefer type 'Trailer' and site 'YouTube'
        for v in videos:
            if v.get("site","").lower() == "youtube" and v.get("type","").lower()=="trailer":
                key = v.get("key")
                if key:
                    return f"https://www.youtube.com/watch?v={key}"
        # fallback: any youtube
        for v in videos:
            if v.get("site","").lower() == "youtube" and v.get("key"):
                return f"https://www.youtube.com/watch?v={v.get('key')}"
        return ""
    except Exception:
        return ""

def fetch_book_cover_google(title, author=""):
    if not title:
        return ""
    try:
        url = "https://www.googleapis.com/books/v1/volumes"
        q = title
        if author:
            q += f" {author}"
        params = {"q": q, "maxResults": 1}
        if GOOGLE_BOOKS_API_KEY:
            params["key"] = GOOGLE_BOOKS_API_KEY
        resp = SESSION.get(url, params=params, timeout=SESSION_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items")
        if items and len(items)>0:
            vol = items[0].get("volumeInfo", {})
            img = vol.get("imageLinks", {})
            return img.get("thumbnail") or img.get("smallThumbnail") or ""
        return ""
    except Exception:
        return ""


def jaccard_score(a_list, b_list):
    a = set(a_list); b = set(b_list)
    if not a and not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter/uni if uni else 0.0

def keyword_overlap(text1, text2):
    if not text1 or not text2:
        return 0
    w1 = set([w for w in re.findall(r"\w+", str(text1).lower()) if len(w) > 3])
    w2 = set([w for w in re.findall(r"\w+", str(text2).lower()) if len(w) > 3])
    if not w1 or not w2:
        return 0
    return len(w1 & w2)

def safe_str_for_poster(val):
    try:
        s = str(val).strip()
        if not s:
            return ""
        low = s.lower()
        if low in ("nan", "none", "<na>"):
            return ""
        if re.search(r"\.(jpg|jpeg|png|webp|gif|svg)(?:$|\?)", low):
            return s
        if "image.tmdb.org" in low or "m.media-amazon.com" in low or "pbs.twimg.com" in low or "images.unsplash.com" in low:
            return s
        if low.startswith("data:image/"):
            return s
        return ""
    except Exception:
        return ""

# -------------------------
# Recommendation engine (returns list of dicts)
def get_similar_movies(selected_title, mode, target_mood=None, goals=None, topk=10):
    if "title" not in movies_df.columns:
        return []
    sel = movies_df[movies_df['title'].str.lower() == selected_title.lower()]
    if sel.empty:
        return []
    sel = sel.iloc[0]
    sel_genres = split_and_clean(sel.get("genre",""))
    sel_cast = split_and_clean(sel.get("cast",""))
    sel_director = str(sel.get("director","")).strip().lower()
    sel_story = str(sel.get("story_tags",""))

    results = []
    for _, row in movies_df.iterrows():
        title = str(row.get("title","")).strip()
        if title.lower() == selected_title.lower():
            continue
        score = 0.0
        reasons = []
        genres = split_and_clean(row.get("genre",""))
        gscore = jaccard_score(sel_genres, genres)
        score += gscore * 5
        if gscore > 0:
            reasons.append(f"genre {int(gscore*100)}%")
        director = str(row.get("director","")).strip().lower()
        if director and sel_director and director == sel_director:
            score += 4
            reasons.append("same director")
        cast = split_and_clean(row.get("cast",""))
        common_cast = len(set(sel_cast) & set(cast))
        if common_cast > 0:
            score += common_cast * 1.5
            reasons.append(f"{common_cast} cast overlap")
        kw = keyword_overlap(sel_story, str(row.get("story_tags","")))
        if kw > 0:
            score += min(kw,5) * 0.5
            reasons.append(f"{kw} story keywords")
        

        # mood/goals scoring omitted here for brevity but can be added similarly
        poster_val = row.get("poster_url", "")
        poster = safe_str_for_poster(poster_val)
        explanation = "; ".join(reasons) if reasons else "Similar content"
        results.append({"title": title, "poster_url": poster, "score": score, "explanation": explanation})
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results[:topk]

def get_similar_books(selected_title, mode, target_mood=None, goals=None, topk=10):
    if "title" not in books_df.columns:
        return []
    sel = books_df[books_df['title'].str.lower() == selected_title.lower()]
    if sel.empty:
        return []
    sel = sel.iloc[0]
    sel_author = str(sel.get("author","")).strip().lower()
    sel_genres = split_and_clean(sel.get("genre",""))
    sel_desc = str(sel.get("description",""))

    results = []
    for _, row in books_df.iterrows():
        title = str(row.get("title","")).strip()
        if title.lower() == selected_title.lower():
            continue
        score = 0.0
        reasons = []
        author = str(row.get("author","")).strip().lower()
        if author and sel_author and author == sel_author:
            score += 5
            reasons.append("same author")
        genres = split_and_clean(row.get("genre",""))
        gscore = jaccard_score(sel_genres, genres)
        score += gscore * 4
        if gscore > 0:
            reasons.append(f"genre {int(gscore*100)}%")
        kw = keyword_overlap(sel_desc, str(row.get("description","")))
        if kw > 0:
            score += min(kw,5) * 0.6
            reasons.append(f"{kw} desc keywords")
        
        poster_val = row.get("cover_url", "")
        poster = safe_str_for_poster(poster_val)
        explanation = "; ".join(reasons) if reasons else "Similar content"
        results.append({"title": title, "poster_url": poster, "score": score, "explanation": explanation})
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results[:topk]
# ---------------- SIDEBAR (Visible only after login & not on login page) ----------------
if st.session_state.user and st.session_state.page != "login":
    st.sidebar.markdown(f"### 👋 Welcome, {st.session_state.user['name']}")

    if st.sidebar.button("View Watchlist"):
        go_to("watchlist")
        st.rerun()

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.session_state.page = "login"
        st.rerun()


# -------------------------
# Pages: login / mode / search / detail
# LOGIN page
if st.session_state.page == "login":
    
    # Add login page identifier for background styling
    st.markdown('<div class="login-page"></div>', unsafe_allow_html=True)



    st.markdown("<div class='title'>AI Book & Movie Recommendation System</div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Sign In"):
            success, data = login_user(email, password)

            if success:
                st.session_state.user = data   # ✅ data MUST be a dict
                go_to("mode")
                st.rerun()
            else:
                st.error(data)


    with tab2:
        name = st.text_input("Name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")

        if st.button("Create Account"):
            success, msg = register_user(email, password, name)
            if success:
                st.success(msg)
            else:
                st.error(msg)


# MODE page
elif st.session_state.page == "mode":

    st.markdown('<div class="title">Recommendation Mode & Preferences</div>', unsafe_allow_html=True)
    mode_local = st.radio(
        "Recommendation Mode",
        [
            "Mood + Goal Based Recommendation",
            "Normal Similarity Recommendation"
        ],
        index=1,
        key="w_mode"
    )

    if mode_local != "Normal Similarity Recommendation":
        st.selectbox("How are you feeling now?", 
                     ["Happy","Sad","Stressed","Bored","Excited","Tired"], 
                     key="w_current_mood")

        st.selectbox("How do you want to feel?", 
                     ["Relaxed","Motivated","Entertained","Same"], 
                     key="w_target_mood")

        st.multiselect(
            "What do you want to improve?",
            ["Improve English","Be Motivated","Learn Business","Learn History","Improve Creativity"],
            key="w_goals"
        )
    st.radio("Recommend:", ["Movies","Books"], index=0, key="w_content_type")

    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Back to Login", key="btn_back_login"):
            go_to("login")
            st.rerun()
    with c2:
        if st.button("Continue", key="btn_continue"):
            st.session_state.mode = st.session_state.get("w_mode")
            st.session_state.use_search = st.session_state.mode != "Mood + Goal Based Recommendation"
            st.session_state.use_mood = st.session_state.mode != "Normal Similarity Recommendation"
            st.session_state.current_mood = st.session_state.get("w_current_mood", None)
            st.session_state.target_mood = st.session_state.get("w_target_mood", None)
            st.session_state.goals = st.session_state.get("w_goals", []) or []
            st.session_state.content_type = st.session_state.get("w_content_type", "Movies")
            st.session_state.selected_title = ""
            st.session_state.last_recs = None
            go_to("search")
            st.rerun()

# SEARCH & RECOMMEND page
elif st.session_state.page == "search":
   
    colA, colB = st.columns([6,1])
    with colB:
        with st.expander("👤 Profile"):
            st.write(st.session_state.user["email"])
            if st.button("View Watchlist"):
                go_to("watchlist")
                st.rerun()
            if st.button("Logout"):
                st.session_state.clear()
                st.session_state.page = "login"
                st.rerun()


    # SHOW SEARCH ONLY FOR SIMILARITY MODES
    query = ""
    if st.session_state.mode != "Mood + Goal Based Recommendation":
        st.markdown(
            "<div class='subtitle'>Type a partial title; matching results appear below. Click a match then \"Recommend\".</div>",
            unsafe_allow_html=True
        )
        query = st.text_input(
            "",
            value=st.session_state.search_text,
            placeholder="Type a movie or book title (partial name)..."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # titles list
    if st.session_state.get("content_type","Movies") == "Movies":
        titles = movies_df["title"].fillna("").tolist() if "title" in movies_df.columns else []
    else:
        titles = books_df["title"].fillna("").tolist() if "title" in books_df.columns else []

    matches = []
    if query.strip():
        q = query.lower().strip()
        
        exact = [t for t in titles if t.lower() == q]
        starts = [t for t in titles if t.lower().startswith(q) and t not in exact]
        contains = [t for t in titles if q in t.lower() and t not in exact + starts]
        
        matches = exact + starts + contains
        matches = matches[:30]


    if matches:
        for i, m in enumerate(matches):
            btn_key = f"match_{i}"
            if i < 8:
                if st.button(m, key=btn_key):
                    st.session_state.selected_title = m
                    st.session_state.search_text = m   # ✅ safe
                    st.rerun()

            else:
                if st.button(m, key=btn_key):
                    st.session_state.selected_title = m
                    st.session_state.search_text = m   # ✅ safe
                    st.rerun()


        if len(matches) > 8:
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:var(--muted);padding:8px 0'>Click Recommend to See Recommendations</div>", unsafe_allow_html=True)

    rcol1, rcol2 = st.columns([1,1])
    with rcol1:
        if st.button("Recommend", key="btn_recommend"):
            mode = st.session_state.mode
            
            # Only require title for similarity-based modes
            if mode != "Mood + Goal Based Recommendation" and not st.session_state.selected_title:
                st.warning("Please select a title first.")
                st.stop()
            else:
                recs = []  # ✅ ADD THIS LINE (FIXES NameError)
                
                sel = st.session_state.selected_title
                target_mood = st.session_state.get("target_mood")
                content = st.session_state.content_type
                goals = st.session_state.get("goals", [])

                # Behaviour 1: Mood + Goal ONLY
                if mode == "Mood + Goal Based Recommendation":
                    mood_map = {
                        "happy": ["happy", "fun", "positive", "joy"],
                        "sad": ["sad", "emotional", "dark"],
                        "excited": ["excited", "thrilling", "action"],
                        "relaxed": ["relaxed", "calm", "peaceful", "neutral"],
                        "stressed": ["stress", "tense", "sad"],
                        "bored": ["fun", "entertainment", "excited"],
                        "tired": ["calm", "relaxed", "slow"]
                    }

                    goal_map = {
                        "improve english": ["education", "learning", "language"],
                        "be motivated": ["inspiration", "motivation"],
                        "learn business": ["business", "finance"],
                        "learn history": ["history", "biography"],
                        "improve creativity": ["creativity", "art", "writing"]
                    }

                    # Choose dataset
                    df = movies_df.copy() if content == "Movies" else books_df.copy()

                    # Soft Mood Filter (less strict)
                    if target_mood:
                        mapped_moods = mood_map.get(target_mood.lower(), [])
                        if mapped_moods:
                            pattern = "|".join(mapped_moods)
                            filtered = df[df["mood_tag"].str.lower().str.contains(pattern, na=False)]
                            if not filtered.empty:
                                df = filtered

                    # Soft Goal Filter
                    if goals:
                        mapped_goals = []
                        for g in goals:
                            mapped_goals += goal_map.get(g.lower(), [])
                        if mapped_goals:
                            pattern = "|".join(mapped_goals)
                            filtered = df[df["goal_tag"].str.lower().str.contains(pattern, na=False)]
                            if not filtered.empty:
                                df = filtered

                    # If no match, show warning
                    if df.empty:
                        st.warning("No content matches your selected mood and goals.")
                        st.stop()

                    # Display results
                    recs = []
                    for _, row in df.head(30).iterrows():
                        poster = safe_str_for_poster(
                            row.get("poster_url" if content == "Movies" else "cover_url", "")
                        )
                        recs.append({
                            "title": row["title"],
                            "poster_url": poster,
                            "explanation": f"Matches mood ({target_mood}) and goals ({', '.join(goals)})"
                        })

                # Behaviour 2: Normal Similarity ONLY
                elif mode == "Normal Similarity Recommendation":
                    if content == "Movies":
                        recs = get_similar_movies(sel, mode)
                    else:
                        recs = get_similar_books(sel, mode)
                st.session_state.last_recs = recs

    with rcol2:
        if st.button("⚙ Change Preferences", key="btn_change"):
            go_to("mode")
            st.rerun()

    st.markdown("---")

    # Display recommendations
    recs = st.session_state.get("last_recs", None)
    if recs:
        grid_cols = st.columns(5)
        mode = st.session_state.mode
        # Behaviour 1 → show ALL
        if mode == "Mood + Goal Based Recommendation":
            display_recs = recs
        else:
            display_recs = recs[:10]   # Behaviour 2 & 3 → only 10
        for i, r in enumerate(display_recs):

            col = grid_cols[i % 5]
            with col:
                poster = r.get("poster_url","") or ""
                if not poster:
                    if st.session_state.get("content_type","Movies") == "Movies":
                        poster = fetch_movie_poster_tmdb(r["title"])
                    else:
                        author = ""
                        try:
                            df = books_df[books_df["title"].str.lower() == r["title"].strip().lower()]
                            if not df.empty and "author" in df.columns:
                                author = df.iloc[0].get("author","")
                        except Exception:
                            author = ""
                        poster = fetch_book_cover_google(r["title"], author)
                if not poster:
                    poster = "https://placehold.co/200x300?text=No+Image&font=roboto"

                safe_title = html_lib.escape(r.get("title",""))
                safe_explain = html_lib.escape(r.get("explanation",""))


                # ✅ POSTER (Streamlit-safe)
                st.image(
                    poster if poster else "https://via.placeholder.com/300x450?text=No+Poster",
                    use_container_width=True
                )

                # ✅ TITLE
                st.markdown(f"**{safe_title}**")

                # ✅ EXPLANATION
                st.caption(safe_explain)

             
                # View Details button (reliable Python callback)
                view_key = f"view_{i}_{safe_title}"
                if st.button("View Details", key=view_key):
                    detail = {"title": r.get("title",""), "poster": poster, "explanation": r.get("explanation","")}
                    try:
                        if st.session_state.get("content_type","Movies") == "Movies":
                            row = movies_df[movies_df["title"].str.lower() == r.get("title","").strip().lower()]
                            if not row.empty:
                                row0 = row.iloc[0]
                                detail["cast"] = str(row0.get("cast",""))
                                detail["director"] = str(row0.get("director",""))
                                detail["story"] = str(row0.get("story_tags",""))
                        else:
                            row = books_df[books_df["title"].str.lower() == r.get("title","").strip().lower()]
                            if not row.empty:
                                row0 = row.iloc[0]
                                detail["author"] = str(row0.get("author",""))
                                detail["story"] = str(row0.get("description",""))
                    except Exception:
                        pass
                    # extract top-3 reasons from explanation
                    expl = detail.get("explanation","")
                    reasons = [x.strip() for x in expl.split(";") if x.strip()]
                    detail["top_reasons"] = reasons[:3]
                    # fetch trailer URL if TMDB key present
                    if TMDB_API_KEY:
                        try:
                            trailer = fetch_trailer_youtube(detail.get("title",""))
                            if trailer:
                                detail["trailer"] = trailer
                        except Exception:
                            detail["trailer"] = ""
                    st.session_state.detail_item = detail
                    go_to("detail")
                    st.rerun()

# DETAIL page
elif st.session_state.page == "detail":
    
    item = st.session_state.get("detail_item", None)
    if not item:
        st.warning("No detail available — returning to recommendations.")
        go_to("search")
        st.rerun()

    else:
        st.markdown('<div style="display:flex;justify-content:space-between;align-items:center"><div class="title">Detail</div></div>', unsafe_allow_html=True)
        # Back button
        back_col, spacer = st.columns([1,5])
        with back_col:
            if st.button("← Back to Recommendations", key="btn_back_from_detail"):
                # clear detail-related state FIRST
                st.session_state.detail_item = None
                st.session_state.last_recs = None
                st.session_state.recs = []
                st.session_state.do_recommend = False

                # behaviour-1 cleanup
                if st.session_state.mode == "Normal Similarity Recommendation":
                    st.session_state.selected_title = ""
                    st.session_state.search_text = ""

                goto_page("search")

        c1, c2 = st.columns([1,2])
        
        with c1:
            poster = item.get("poster","")

            if isinstance(poster, str) and poster.strip():
                st.image(poster, use_container_width=True)
            else:
                st.image(
                    "https://placehold.co/400x600?text=No+Image&font=roboto",
                    use_container_width=True
                )

            
            if st.button("Add to Watchlist", key=f"watch_{item.get('title','')}"):
                content_type = "Book" if st.session_state.content_type == "Books" else "Movie"
                # default safety
                watch_item = {
                    "id": f"{content_type.lower()}_{item.get('title','')}",
                    "title": item.get("title", ""),
                    "content_type": content_type
                }

                add_to_watchlist(
                    st.session_state.user["email"],
                    watch_item
                )
                st.success("Added to watchlist")

            # ---------------- MOVIE AFFILIATE (DETAIL PAGE ONLY) ----------------
            if st.session_state.content_type == "Movies":
                st.markdown("### 🎬 Watch This Movie")

                title = item.get("title", "")
                prime_link = amazon_movie_affiliate_link(title)

                if prime_link:
                    # ✅ Amazon Prime (Affiliate)
                    st.markdown(
                        f"""
                        <a href="{prime_link}" target="_blank" class="affiliate-btn">
                            ▶ Watch on Amazon Prime
                        </a>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    # ❌ Not on Prime → show other platforms
                    st.markdown(
                        f"""
                        <a href="https://www.netflix.com/search?q={title}"
                            target="_blank" class="affiliate-btn">
                            🔍 Search on Netflix
                        </a>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                    f"""
                        <a href="https://www.hotstar.com/in/search?q={title}"
                            target="_blank" class="affiliate-btn">
                            🔍 Search on JioHotstar
                        </a>
                        """,
                        unsafe_allow_html=True
                    )

  
        with c2:
            st.markdown(f"### {html_lib.escape(item.get('title',''))}")
            st.markdown(f"**Why recommended:** {html_lib.escape(item.get('explanation',''))}")
            # top 3 reasons
            top_reasons = item.get("top_reasons", [])
            if top_reasons:
                st.markdown("**Top reasons:**")
                for rr in top_reasons:
                    st.write("- " + rr)
            if item.get("story"):
                st.markdown("**Synopsis**")
                st.write(item.get("story"))
            if item.get("cast"):
                st.markdown("**Cast**")
                st.write(item.get("cast"))
            if item.get("director"):
                st.markdown("**Director**")
                st.write(item.get("director"))
            if item.get("author"):
                st.markdown("**Author**")
                st.write(item.get("author"))
            
            # ---------------- BOOK AFFILIATE (DETAIL PAGE ONLY) ----------------
            if st.session_state.content_type == "Books":
                st.markdown("### 📚 Buy This Book")

                title = item.get("title", "")
                author = item.get("author", "")

                book_link = amazon_book_affiliate_link(title, author)

                if book_link:
                    st.markdown(
                        f"""
                        <a href="{book_link}" target="_blank" class="affiliate-btn">
                            🛒 Buy on Amazon
                        </a>
                        """,
                        unsafe_allow_html=True
                    )


            # trailer embedding if available
            trailer = item.get("trailer","")
            if trailer:
                st.markdown("---")
                st.markdown("**Trailer**")
                try:
                    st.video(trailer)
                except Exception:
                    st.markdown(f"[Open trailer]({html_lib.escape(trailer)})")

        st.markdown("<div style='margin-top:16px;color:var(--muted)'>Use the Back button to return to recommendations.</div>", unsafe_allow_html=True)


elif st.session_state.page == "watchlist":
    
    st.markdown("<div class='title'>My Watchlist</div>", unsafe_allow_html=True)

    if st.button("← Back to Recommendations"):
        go_to("search")
        st.rerun()

    # 🔹 Fetch from DB (single source of truth)
    raw_watchlist = get_watchlist(st.session_state.user["email"])
    watchlist = [
        w for w in raw_watchlist
        if isinstance(w, dict) and "content_type" in w
    ]

    if not watchlist:
        st.info("Your watchlist is empty.")
    else:
        tab1, tab2 = st.tabs(["🎬 Movies", "📚 Books"])

        # -------- MOVIES --------
        with tab1:
            movies = [w for w in watchlist if w["content_type"] == "Movie"]

            if not movies:
                st.info("No movies in watchlist.")
            else:
                for item in movies:
                    col1, col2 = st.columns([4, 1])
                    col1.write(item["title"])

                    if col2.button("Remove", key=f"rm_movie_{item['id']}"):
                        remove_from_watchlist(
                            st.session_state.user["email"],
                            item["id"]
                        )
                        st.rerun()

        # -------- BOOKS --------
        with tab2:
            books = [w for w in watchlist if w["content_type"] == "Book"]

            if not books:
                st.info("No books in watchlist.")
            else:
                for item in books:
                    col1, col2 = st.columns([4, 1])
                    col1.write(item["title"])

                    if col2.button("Remove", key=f"rm_book_{item['id']}"):
                        remove_from_watchlist(
                            st.session_state.user["email"],
                            item["id"]
                        )
                        st.rerun()