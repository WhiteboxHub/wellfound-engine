"""
Send jobs from data/wellfound_jobs.json to wbl-backend POST /positions/bulk.

JSON shape matches CSVTracker._write_json: top-level "jobs" array (Hiring Cafe–compatible fields).
"""

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.auth_service import auth_service  # noqa: E402
from core.logger import logger  # noqa: E402
from config.settings import settings  # noqa: E402

SOURCE = "wellfound.com"
DEFAULT_INPUT = ROOT / "data" / "wellfound_jobs.json"
BATCH_SIZE = 50


def _normalize_employment_mode(raw: str) -> str:
    if not raw:
        return "onsite"
    r = raw.strip().lower()
    if "remote" in r:
        return "remote"
    if "hybrid" in r:
        return "hybrid"
    return "onsite"


def _normalize_position_type(raw: str) -> str:
    """Map scraped labels to backend PositionTypeEnum (no part_time)."""
    if not raw:
        return "full_time"
    r = raw.strip().lower()
    if "intern" in r:
        return "internship"
    if "contract" in r and "hire" in r:
        return "contract_to_hire"
    if "contract" in r:
        return "contract"
    return "full_time"


def _api_base_url() -> str:
    auth_url = settings.AUTH_URL or ""
    base = auth_url.replace("/login", "").replace("/api/login", "")
    if "/api" not in base:
        base += "/api"
    return base


def _send_batch(url: str, token: str, batch: list) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, json={"positions": batch}, headers=headers, timeout=60)
        response.raise_for_status()
        res = response.json()
        logger.info(
            f"Batch success: {res.get('inserted', 0)} inserted, "
            f"{res.get('skipped', 0)} duplicates"
        )
    except Exception as e:
        logger.error(f"Failed to send batch to API: {e}")


def ingest_to_api(json_path: Path) -> None:
    if not json_path.exists():
        logger.error(f"File not found: {json_path}")
        return

    token = auth_service.get_access_token()
    if not token:
        logger.error("Failed to obtain authentication token. Set AUTH_URL, AUTH_USERNAME, AUTH_PASSWORD in .env")
        return

    positions_url = f"{_api_base_url().rstrip('/')}/positions/bulk"

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs") or []
    if not jobs:
        logger.warning("No jobs in file; nothing to send.")
        return

    logger.info(f"Ingesting {len(jobs)} job(s) from {json_path}")

    batch: list = []
    sent = 0

    for job in jobs:
        job_id = (job.get("job_id") or "").strip()
        if not job_id:
            ju = (job.get("job_url") or job.get("url") or "").strip()
            job_id = ju.rstrip("/").split("/")[-1] if ju else ""
        if not job_id:
            logger.warning("Skipping job with no job_id and no usable URL id")
            continue

        title = (job.get("job_tittle") or job.get("title") or "unknown title")[:255]
        company = (job.get("comapany") or job.get("company") or "unknown company")[:255]
        location = job.get("location")
        combined_type = " ".join(
            filter(
                None,
                [str(job.get("type") or ""), str(job.get("position_type") or "")],
            )
        )
        employment_mode = _normalize_employment_mode(combined_type)
        position_type = _normalize_position_type(combined_type)

        job_listing = {
            "title": title.lower() if title else title,
            "company_name": company.lower() if company else company,
            "location": location.lower() if location else location,
            "city": None,
            "state": None,
            "country": None,
            "position_type": position_type,
            "employment_mode": employment_mode,
            "source": SOURCE,
            "source_uid": str(job_id),
            "job_url": job.get("job_url") or job.get("url"),
            "description": job.get("company_description"),
            "status": "open",
        }
        batch.append(job_listing)

        if len(batch) >= BATCH_SIZE:
            _send_batch(positions_url, token, batch)
            sent += len(batch)
            batch = []

    if batch:
        _send_batch(positions_url, token, batch)
        sent += len(batch)

    logger.info(f"Finished. Total positions sent to API: {sent}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Wellfound JSON into wbl-backend job_listing.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to wellfound jobs JSON (default: {DEFAULT_INPUT})",
    )
    args = parser.parse_args()
    ingest_to_api(args.input)
