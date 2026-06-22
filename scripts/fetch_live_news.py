import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import init_db
from app.services.news_ingestion import DEFAULT_RSS_FEEDS, fetch_live_news


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch current publisher RSS news into Bản Đồ Tin.")
    parser.add_argument("--source", default="vnexpress", choices=sorted(DEFAULT_RSS_FEEDS))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--rss-only", action="store_true", help="Do not fetch article HTML; use RSS title/summary only.")
    args = parser.parse_args()

    init_db()
    result = fetch_live_news(source_key=args.source, limit=args.limit, fetch_full_text=not args.rss_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
