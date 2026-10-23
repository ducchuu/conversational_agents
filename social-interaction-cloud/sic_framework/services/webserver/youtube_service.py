import logging
import os
from functools import lru_cache

from flask import Blueprint, jsonify, request

from sic_framework.services.webserver.telemetry import telemetry

logger = logging.getLogger(__name__)

youtube_bp = Blueprint("youtube", __name__)


@lru_cache(maxsize=512)
def fetch_cached_youtube_video_id(title: str, api_key: str):
    """
    Cached YouTube video lookup. Prevents consuming the 10,000 units/day quota
    on repeated recipe views and browser reloads.
    """
    import requests
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": f"{title} recipe",
        "type": "video",
        "maxResults": 1,
        "safeSearch": "strict",
        "key": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            logger.error(f"YouTube Data API error ({r.status_code}): {r.text}")
            return None
        items = r.json().get("items", [])
        return items[0].get("id", {}).get("videoId") if items else None
    except Exception as e:
        logger.error(f"YouTube Data API request exception: {e}")
        return None


def search_youtube_video(title: str, api_key: str):
    """Fetch a YouTube video ID for a recipe title and record cache hit telemetry."""
    cached_info = fetch_cached_youtube_video_id.cache_info()
    curr_hits = cached_info.hits
    video_id = fetch_cached_youtube_video_id(title, api_key)
    new_info = fetch_cached_youtube_video_id.cache_info()
    telemetry.record_youtube_cache(hit=(new_info.hits > curr_hits))
    return video_id


@youtube_bp.route("/api/youtube/search", methods=["GET"])
def youtube_search():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return jsonify({"error": "Missing YOUTUBE_API_KEY"}), 500

    title = (request.args.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Missing title"}), 400

    try:
        video_id = search_youtube_video(title, api_key)
        return jsonify({"videoId": video_id})
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return jsonify({"videoId": None}), 502
