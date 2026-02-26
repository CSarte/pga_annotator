#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -r requirements.txt

# Download + unzip Roboflow dataset into roboflow_dataset/
curl -L "https://app.roboflow.com/ds/A7xPEnoo9d?key=e8aA6h5DxM" -o roboflow.zip
rm -rf roboflow_dataset
mkdir -p roboflow_dataset
unzip -q roboflow.zip -d roboflow_dataset
rm roboflow.zip

# Seed database (Neon) with images if missing
python seed_images.py