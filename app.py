import os
import time
from typing import Dict

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session
from sqlalchemy.sql import exists, func

from db import get_db, engine
from models import Base, ImageItem, Rating

RATING_FIELDS = ["erythema", "induration", "scaling"]
RATING_MIN, RATING_MAX = 0, 4

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Serve local images in dev or if you're hosting images on server disk
DATASET_ROOT = os.getenv("DATASET_ROOT", "./roboflow_dataset")
DATASET_ROOT = os.path.abspath(DATASET_ROOT)
if os.path.isdir(DATASET_ROOT):
    app.mount("/images", StaticFiles(directory=DATASET_ROOT), name="images")

def compute_overall_pga(erythema: int, induration: int, scaling: int) -> int:
    # Option A: rounded average
    overall = round((erythema + induration + scaling) / 3)
    return max(0, min(4, int(overall)))

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def validate_rating(val: int):
    if not (RATING_MIN <= val <= RATING_MAX):
        raise HTTPException(status_code=400, detail=f"Ratings must be {RATING_MIN}-{RATING_MAX}")


@app.get("/api/next")
def next_image(username: str, subset: str = "all", db: Session = Depends(get_db)):
    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    q = db.query(ImageItem)
    if subset != "all":
        q = q.filter(ImageItem.subset == subset)

    # Find an image not yet rated by this username
    item = (
        q.filter(~exists().where((Rating.username == username) & (Rating.image_id == ImageItem.image_id)))
        .order_by(func.random())
        .limit(1)
        .first()
    )

    if not item:
        return {"done": True, "message": "No more unrated images for this user/subset."}

    # Prefer image_url (production object storage), else serve local file via /images/*
    if item.image_url:
        url = item.image_url
    else:
        url = f"/images/{item.image_relpath}"

    return {"done": False, "image_id": item.image_id, "subset": item.subset, "image_url": url}


@app.post("/api/submit")
def submit(payload: Dict, db: Session = Depends(get_db)):
    username = str(payload.get("username", "")).strip()
    image_id = str(payload.get("image_id", "")).strip()
    subset = str(payload.get("subset", "")).strip()

    if not username or not image_id or not subset:
        raise HTTPException(status_code=400, detail="username, image_id, subset required")

    ratings = {}
    for f in RATING_FIELDS:   # now only erythema, induration, scaling
        if f not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {f}")
        try:
            val = int(payload[f])
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid int for {f}")
        validate_rating(val)
        ratings[f] = val

    # ✅ Compute overall automatically
    overall_pga = compute_overall_pga(
        ratings["erythema"],
        ratings["induration"],
        ratings["scaling"],
    )

    now = int(time.time())

    existing = db.query(Rating).filter(
        Rating.username == username,
        Rating.image_id == image_id
    ).first()

    if existing:
        existing.erythema = ratings["erythema"]
        existing.induration = ratings["induration"]
        existing.scaling = ratings["scaling"]
        existing.overall_pga = overall_pga   # ✅ computed value
        existing.subset = subset
        existing.created_at = now
    else:
        db.add(
            Rating(
                username=username,
                image_id=image_id,
                subset=subset,
                erythema=ratings["erythema"],
                induration=ratings["induration"],
                scaling=ratings["scaling"],
                overall_pga=overall_pga,   # ✅ computed value
                created_at=now,
            )
        )

    db.commit()
    return {"ok": True}