from db import get_db
import hashlib

db = get_db()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(email, password, name):
    hashed_pw = hash_password(password)

    db = get_db()
    user_ref = db.collection("users").document(email)

    if user_ref.get().exists:
        return False, "User already exists"

    user_ref.set({
        "email": email,
        "name": name,
        "password": hashed_pw
    })

    return True, "User registered successfully"

def login_user(email, password):
    db = get_db()
    user_ref = db.collection("users").document(email)
    doc = user_ref.get()

    if not doc.exists:
        return False, "User not found"

    user = doc.to_dict()
    hashed_pw = hash_password(password)

    if user["password"] != hashed_pw:
        return False, "Incorrect password"

    return True, {
        "email": user["email"],
        "name": user["name"]
    }

def add_to_watchlist(email, item):
    user_ref = db.collection("users").document(email)
    user = user_ref.get().to_dict()

    raw_watchlist = user.get("watchlist", [])

    # ✅ FIX: keep only valid dict items
    watchlist = [w for w in raw_watchlist if isinstance(w, dict)]

    # prevent duplicates safely
    if any(w.get("id") == item.get("id") for w in watchlist):
        return

    watchlist.append(item)
    user_ref.update({"watchlist": watchlist})


def get_watchlist(email):
    user = db.collection("users").document(email).get().to_dict()
    return user.get("watchlist", [])


def remove_from_watchlist(email, item_id):
    user_ref = db.collection("users").document(email)
    user = user_ref.get().to_dict()

    watchlist = [
        w for w in user.get("watchlist", [])
        if w["id"] != item_id
    ]

    user_ref.update({"watchlist": watchlist})


