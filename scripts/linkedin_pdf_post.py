#!/usr/bin/env python3
"""
Upload LTG carousel PDFs to LinkedIn and publish them as native document posts.

By default this script runs in dry-run mode. Pass --publish to create real
LinkedIn posts.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_DIR = SITE_ROOT / "insights"
INSIGHTS_JSON = SITE_ROOT / "insights.json"
ENV_PATH = SCRIPT_DIR / ".env"
SITE_URL = os.environ.get("SITE_URL", "https://lighttowergroup.co").rstrip("/")
LINKEDIN_VERSION = os.environ.get("LINKEDIN_VERSION", "202506")


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def redact_secret_text(value: object) -> str:
    text = str(value)
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    if token:
        text = text.replace(token, "[REDACTED]")
    return text


def linkedin_headers(content_type: str | None = "application/json") -> dict:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def validate_linkedin_env() -> tuple[str, str]:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    owner = os.environ.get("LINKEDIN_OWNER_URN") or os.environ.get("LINKEDIN_PERSON_URN", "")
    if not token or not owner:
        raise RuntimeError(
            "LinkedIn PDF posting needs LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN "
            "or LINKEDIN_OWNER_URN in scripts/.env. Run linkedin_auth.py first."
        )
    return token, owner


def warn_token_expiry() -> None:
    expiry = os.environ.get("LINKEDIN_TOKEN_EXPIRY", "")
    if not expiry:
        return
    try:
        days_left = (datetime.strptime(expiry, "%Y-%m-%d").date() - datetime.now().date()).days
    except ValueError:
        return
    if days_left < 0:
        raise RuntimeError(f"LinkedIn token expired on {expiry}. Re-run linkedin_auth.py.")
    if days_left <= 7:
        print(f"  [WARN] LinkedIn token expires in {days_left} day(s). Refresh soon.")


def load_insights() -> list[dict]:
    if not INSIGHTS_JSON.exists():
        return []
    return json.loads(INSIGHTS_JSON.read_text(encoding="utf-8"))


def resolve_articles(slugs: Iterable[str] | None, latest: int | None) -> list[dict]:
    insights = load_insights()
    by_slug = {item.get("slug"): item for item in insights if item.get("slug")}

    if slugs:
        articles = []
        for slug in slugs:
            article = by_slug.get(slug, {"slug": slug, "title": slug.replace("-", " ").title()})
            articles.append(article)
        return articles

    limit = latest or 10
    return insights[:limit]


def pdf_path_for(article: dict) -> Path:
    return INSIGHTS_DIR / f"{article['slug']}_carousel.pdf"


def post_text_for(article: dict) -> str:
    slug = article["slug"]
    schema_path = INSIGHTS_DIR / f"{slug}_carousel-data.json"
    sidecar = INSIGHTS_DIR / f"linkedin-post-{slug}.txt"

    if schema_path.exists():
        sys.path.insert(0, str(SCRIPT_DIR))
        from build_linkedin_post import build_linkedin_post_text

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        text = build_linkedin_post_text(schema).strip()
    elif sidecar.exists():
        text = sidecar.read_text(encoding="utf-8").strip()
    else:
        title = (article.get("title") or slug.replace("-", " ").title()).strip()
        text = f"{title}\n\nAttached as a Light Tower Group capital markets note."

    if len(text) > 2950:
        text = text[:2940].rsplit(" ", 1)[0].rstrip() + "..."
    return text


def initialize_document_upload(owner_urn: str) -> tuple[str, str]:
    payload = {"initializeUploadRequest": {"owner": owner_urn}}
    response = requests.post(
        "https://api.linkedin.com/rest/documents?action=initializeUpload",
        headers=linkedin_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"initializeUpload failed {response.status_code}: {redact_secret_text(response.text)}")

    value = response.json().get("value", {})
    document_urn = value.get("document")
    upload_url = value.get("uploadUrl") or value.get("uploadUrlExpiresAt")
    if not document_urn or not upload_url or upload_url == value.get("uploadUrlExpiresAt"):
        raise RuntimeError(f"initializeUpload response missing document/uploadUrl: {redact_secret_text(response.text)}")
    return document_urn, upload_url


def upload_pdf(upload_url: str, pdf_path: Path) -> None:
    response = requests.put(
        upload_url,
        headers={"Content-Type": "application/pdf"},
        data=pdf_path.read_bytes(),
        timeout=120,
    )
    if response.status_code not in (200, 201, 202):
        raise RuntimeError(f"PDF upload failed {response.status_code}: {redact_secret_text(response.text)}")


def wait_for_document_available(document_urn: str, timeout_seconds: int = 90) -> None:
    encoded = quote(document_urn, safe="")
    deadline = time.time() + timeout_seconds
    last_status = "PROCESSING"

    while time.time() < deadline:
        response = requests.get(
            f"https://api.linkedin.com/rest/documents/{encoded}",
            headers=linkedin_headers(content_type=None),
            timeout=20,
        )
        if response.status_code == 404:
            time.sleep(3)
            continue
        if response.status_code not in (200, 201):
            raise RuntimeError(f"document status failed {response.status_code}: {redact_secret_text(response.text)}")

        value = response.json()
        last_status = (
            value.get("status")
            or value.get("processingStatus")
            or value.get("lifecycleState")
            or "UNKNOWN"
        )
        if str(last_status).upper() in {"AVAILABLE", "READY"}:
            return
        if str(last_status).upper() in {"PROCESSING_FAILED", "FAILED"}:
            raise RuntimeError(f"LinkedIn document processing failed: {redact_secret_text(value)}")
        time.sleep(4)

    raise RuntimeError(f"Timed out waiting for LinkedIn document processing; last status={last_status}")


def create_document_post(owner_urn: str, document_urn: str, title: str, commentary: str) -> str:
    payload = {
        "author": owner_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {
                "id": document_urn,
                "title": title[:200],
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers=linkedin_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"post create failed {response.status_code}: {redact_secret_text(response.text)}")
    return response.headers.get("x-restli-id", "unknown")


def post_article_pdf(article: dict, dry_run: bool = True) -> dict:
    slug = article["slug"]
    pdf_path = pdf_path_for(article)
    if not pdf_path.exists():
        return {"slug": slug, "ok": False, "error": f"missing PDF: {pdf_path.relative_to(SITE_ROOT)}"}

    title = (article.get("title") or slug.replace("-", " ").title()).strip()
    commentary = post_text_for(article)

    if dry_run:
        print(f"  [DRY-RUN] {slug}: would upload {pdf_path.relative_to(SITE_ROOT)}")
        print(f"            title: {title[:100]}")
        print(f"            caption: {commentary[:180].replace(chr(10), ' ')}...")
        return {"slug": slug, "ok": True, "dry_run": True}

    _, owner_urn = validate_linkedin_env()
    document_urn, upload_url = initialize_document_upload(owner_urn)
    upload_pdf(upload_url, pdf_path)
    wait_for_document_available(document_urn)
    post_id = create_document_post(owner_urn, document_urn, title, commentary)
    print(f"  LinkedIn PDF: posted {slug} (post id: {post_id})")
    return {"slug": slug, "ok": True, "post_id": post_id, "document": document_urn}


def post_article_pdfs(articles: list[dict], dry_run: bool = True) -> dict:
    load_env()
    if not dry_run:
        validate_linkedin_env()
        warn_token_expiry()

    results = []
    for article in articles:
        try:
            results.append(post_article_pdf(article, dry_run=dry_run))
        except Exception as exc:
            slug = article.get("slug", "unknown")
            error = redact_secret_text(exc)
            print(f"  [WARN] LinkedIn PDF failed for {slug}: {error}")
            results.append({"slug": slug, "ok": False, "error": error})

    ok_count = sum(1 for result in results if result.get("ok"))
    return {
        "ok": ok_count == len(results),
        "posted_count": ok_count,
        "attempted_count": len(results),
        "dry_run": dry_run,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Post LTG carousel PDFs to LinkedIn")
    parser.add_argument("--slug", action="append", help="Article slug to post. Repeat for multiple articles.")
    parser.add_argument("--latest", type=int, default=10, help="Post the latest N insights from insights.json.")
    parser.add_argument("--publish", action="store_true", help="Create real LinkedIn posts. Default is dry-run.")
    args = parser.parse_args()

    articles = resolve_articles(args.slug, args.latest)
    if not articles:
        print("No articles found.")
        return 1

    result = post_article_pdfs(articles, dry_run=not args.publish)
    print(
        f"\nLinkedIn PDF batch: {result['posted_count']}/{result['attempted_count']} "
        f"{'validated' if result['dry_run'] else 'posted'}"
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
