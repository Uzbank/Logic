"""YouTube Data API v3: auth, niche research, upload, scheduling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import env, log

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=env("YT_REFRESH_TOKEN"),
        client_id=env("YT_CLIENT_ID"),
        client_secret=env("YT_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def niche_snapshot(yt, keywords: list[str], days: int = 21, per_kw: int = 8) -> list[dict]:
    """Top recent videos for each seed keyword, with view counts. ~100 quota units per keyword."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids, rows = [], {}
    for kw in keywords:
        res = yt.search().list(
            q=kw, part="snippet", type="video", order="viewCount",
            publishedAfter=since, maxResults=per_kw, relevanceLanguage="en", regionCode="US",
        ).execute()
        for it in res.get("items", []):
            vid = it["id"]["videoId"]
            if vid not in rows:
                ids.append(vid)
                rows[vid] = {"title": it["snippet"]["title"], "channel": it["snippet"]["channelTitle"], "keyword": kw}
    for i in range(0, len(ids), 50):
        stats = yt.videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute()
        for it in stats.get("items", []):
            rows[it["id"]]["views"] = int(it["statistics"].get("viewCount", 0))
    out = sorted(rows.values(), key=lambda r: r.get("views", 0), reverse=True)
    log(f"YouTube niche snapshot: {len(out)} recent videos")
    return out


def upload(yt, video: Path, thumb: Path | None, plan: dict, cfg: dict, publish_at: datetime | None) -> str:
    from googleapiclient.http import MediaFileUpload

    y = cfg["youtube"]
    status = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": bool(y["made_for_kids"]),
    }
    if publish_at:
        status["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    tags = list(dict.fromkeys(plan["tags"] + y["default_tags"]))
    # YouTube limit: 500 chars total for tags
    while len(",".join(tags)) > 480:
        tags.pop()
    body = {
        "snippet": {
            "title": plan["title"][:100],
            "description": plan["description"][:4900],
            "tags": tags,
            "categoryId": y["category_id"],
            "defaultLanguage": cfg["channel"]["language"],
            "defaultAudioLanguage": cfg["channel"]["language"],
        },
        "status": status,
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st:
            log(f"Upload {int(st.progress() * 100)}%")
    vid = resp["id"]
    log(f"Uploaded: https://youtu.be/{vid}")
    if thumb:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/png")).execute()
        except Exception as e:  # channel must be phone-verified for custom thumbnails
            log(f"Thumbnail not set ({e}). Verify the channel phone number in YouTube Studio.")
    if y.get("playlist_id"):
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": y["playlist_id"], "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
    return vid


def set_schedule(yt, video_id: str, cfg: dict, publish_at: datetime | None) -> None:
    """publish_at=None keeps the video private with no schedule (cancelled)."""
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": bool(cfg["youtube"]["made_for_kids"])}
    if publish_at:
        if publish_at <= datetime.now(timezone.utc) + timedelta(minutes=10):
            status = {"privacyStatus": cfg["youtube"]["privacy_after_publish"],
                      "selfDeclaredMadeForKids": status["selfDeclaredMadeForKids"]}
        else:
            status["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    yt.videos().update(part="status", body={"id": video_id, "status": status}).execute()
    log(f"Video {video_id} status -> {status}")
