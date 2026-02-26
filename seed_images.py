import os
from sqlalchemy.orm import Session

from db import engine, SessionLocal
from models import Base, ImageItem

ALLOWED_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

def detect_subset(path: str) -> str:
    p = path.replace("\\", "/")
    if "/train/" in p:
        return "train"
    if "/valid/" in p:
        return "valid"
    if "/test/" in p:
        return "test"
    return "unknown"

def rel_id(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace("\\", "/")

def walk_images(root: str):
    for r, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(ALLOWED_EXTS):
                yield os.path.join(r, f)

def main():
    dataset_root = os.getenv("DATASET_ROOT", "./roboflow_dataset")
    dataset_root = os.path.abspath(dataset_root)

    if not os.path.isdir(dataset_root):
        raise SystemExit(f"DATASET_ROOT not found: {dataset_root}")

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        existing = set(x[0] for x in db.query(ImageItem.image_id).all())

        added = 0
        for path in walk_images(dataset_root):
            image_id = rel_id(dataset_root, path)
            if image_id in existing:
                continue
            subset = detect_subset(path)
            db.add(ImageItem(image_id=image_id, subset=subset, image_path=path, image_url=None))
            added += 1

        db.commit()
        total = db.query(ImageItem).count()
        print(f"Seed complete. Added {added} images. Total images in DB: {total}")
    finally:
        db.close()

if __name__ == "__main__":
    main()