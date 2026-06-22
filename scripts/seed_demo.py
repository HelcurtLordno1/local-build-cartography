import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import load_seed_data


if __name__ == "__main__":
    load_seed_data()
    print("Seeded Bản Đồ Tin demo data.")
