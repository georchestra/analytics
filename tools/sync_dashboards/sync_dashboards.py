#!/usr/bin/env python3
"""
Sync Superset dashboards from local .zip exports to a running Superset instance.

Only imports a dashboard if its .zip file hash has changed since the last sync.
The hash of the last successful import is stored as a tag on the dashboard in
Superset itself (e.g. ``zip-sha256:<hex>``), so no local state file is needed.

Uses ``overwrite=true`` so that dashboards matched by UUID keep their IDs.

Usage (classic login):
    python sync_dashboards.py \
        --superset-url http://localhost:8088 \
        --username admin \
        --password admin \
        --dashboards-dir /dashboards

Usage (geOrchestra sec-proxy headers):
    python sync_dashboards.py \
        --superset-url http://localhost:8088 \
        --sec-username analytics_update \
        --sec-roles ROLE_SUPERSET_ADMIN \
        --dashboards-dir /dashboards

    When --sec-username is provided (or SEC_USERNAME is set), authentication
    uses geOrchestra sec-* headers instead of the login API.

Environment variables (fallbacks for CLI options):
    SUPERSET_URL, SUPERSET_USERNAME, SUPERSET_PASSWORD,
    DASHBOARDS_DIR, ANALYTICS_DB_URI,
    SEC_USERNAME, SEC_ROLES, SEC_EMAIL
"""

import argparse
import hashlib
import io
import json
import logging
import os
import re
import sys
import zipfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

TAG_PREFIX = "zip-sha256:"
DASHBOARD_OBJECT_TYPE = 3  # Superset ObjectType enum value for dashboards
DEFAULT_DASHBOARDS_DIR = "/dashboards"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_file_hash(filepath: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    return hashlib.file_digest(open(filepath, "rb"), "sha256").hexdigest()


def extract_dashboard_uuids(zip_path: Path) -> list[str]:
    """Extract dashboard UUIDs from a Superset export zip.

    Reads each ``<root>/dashboards/*.yaml`` entry and looks for the first
    ``uuid:`` line, which is the dashboard's own UUID.
    """
    uuids = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            relative = name.split("/", 1)[1] if "/" in name else name
            if relative.startswith("dashboards/") and relative.endswith(".yaml"):
                with zf.open(name) as entry:
                    for raw_line in entry:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        m = re.match(r"^uuid:\s+(.+)$", line)
                        if m:
                            uuids.append(m.group(1).strip())
                            break  # first uuid in the file is the dashboard's
    return uuids


def patch_zip_database_uri(zip_path: Path, db_uri: str) -> io.BytesIO:
    """Return a new in-memory zip with ``sqlalchemy_uri`` replaced in all database configs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(zip_path) as src, zipfile.ZipFile(buf, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            relative = item.filename.split("/", 1)[1] if "/" in item.filename else item.filename
            if relative.startswith("databases/") and relative.endswith(".yaml"):
                text = data.decode("utf-8")
                text = re.sub(
                    r"(sqlalchemy_uri:\s*).*",
                    rf"\g<1>{db_uri}",
                    text,
                )
                data = text.encode("utf-8")
                logger.info("Patched sqlalchemy_uri in %s", item.filename)
            dst.writestr(item, data)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Superset client
# ---------------------------------------------------------------------------

class SupersetClient:
    """Minimal Superset REST API client for dashboard import & tagging."""

    def __init__(self, base_url: str, db_uri: str | None = None,
                 username: str | None = None, password: str | None = None,
                 sec_username: str | None = None, sec_roles: str | None = None,
                 sec_email: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.db_uri = db_uri
        self.session = requests.Session()

        # Auth mode: geOrchestra sec-headers or classic username/password
        self._use_georchestra = bool(sec_username)
        if self._use_georchestra:
            self.session.headers.update({"sec-username": sec_username})
            if sec_roles:
                self.session.headers.update({"sec-roles": sec_roles})
            if sec_email:
                self.session.headers.update({"sec-email": sec_email})
        else:
            self._username = username
            self._password = password

    # -- auth ---------------------------------------------------------------

    def login(self) -> None:
        if self._use_georchestra:
            logger.info("Using geOrchestra sec-header authentication (sec-username: %s)",
                        self.session.headers.get("sec-username"))
            return

        url = f"{self.base_url}/api/v1/security/login"
        payload = {
            "username": self._username,
            "password": self._password,
            "provider": "db",
            "refresh": True,
        }
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        logger.info("Authenticated with Superset as '%s'", self._username)

    def _csrf_token(self) -> str:
        resp = self.session.get(f"{self.base_url}/api/v1/security/csrf_token/")
        resp.raise_for_status()
        return resp.json()["result"]

    def _csrf_headers(self) -> dict:
        token = self._csrf_token()
        return {"X-CSRFToken": token, "Referer": self.base_url}

    # -- dashboard lookup ---------------------------------------------------

    def find_dashboard_by_uuid(self, uuid: str) -> dict | None:
        """Return the dashboard dict for a given UUID, or None."""
        # The uuid column is not exposed as a filterable field in the Superset
        # API, so we fetch all dashboards and match client-side.
        page_size = 100
        page = 0
        while True:
            rison = f"(page:{page},page_size:{page_size})"
            resp = self.session.get(f"{self.base_url}/api/v1/dashboard/?q={rison}")
            resp.raise_for_status()
            results = resp.json().get("result", [])
            for dash in results:
                if dash.get("uuid") == uuid:
                    return dash
            if len(results) < page_size:
                return None
            page += 1

    # -- tags ---------------------------------------------------------------

    def get_hash_tag(self, dashboard_id: int) -> str | None:
        """Read the zip-sha256 tag from a dashboard. Returns the hash or None."""
        resp = self.session.get(f"{self.base_url}/api/v1/dashboard/{dashboard_id}")
        resp.raise_for_status()
        tags = resp.json().get("result", {}).get("tags", [])
        for tag in tags:
            name = tag.get("name", "")
            if name.startswith(TAG_PREFIX):
                return name[len(TAG_PREFIX):]
        return None

    def set_hash_tag(self, dashboard_id: int, file_hash: str) -> None:
        """Set the zip-sha256 tag on a dashboard, removing any previous one."""
        self._remove_hash_tags(dashboard_id)

        tag_name = f"{TAG_PREFIX}{file_hash}"
        resp = self.session.post(
            f"{self.base_url}/api/v1/tag/{DASHBOARD_OBJECT_TYPE}/{dashboard_id}/",
            json={"properties": {"tags": [tag_name]}},
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        logger.debug("Set tag '%s' on dashboard %d", tag_name, dashboard_id)

    def _remove_hash_tags(self, dashboard_id: int) -> None:
        """Remove all existing zip-sha256 tags from a dashboard."""
        resp = self.session.get(f"{self.base_url}/api/v1/dashboard/{dashboard_id}")
        resp.raise_for_status()
        tags = resp.json().get("result", {}).get("tags", [])
        for tag in tags:
            name = tag.get("name", "")
            if name.startswith(TAG_PREFIX):
                del_resp = self.session.delete(
                    f"{self.base_url}/api/v1/tag/{DASHBOARD_OBJECT_TYPE}/{dashboard_id}/{name}",
                    headers=self._csrf_headers(),
                )
                if del_resp.ok:
                    logger.debug("Removed old tag '%s' from dashboard %d", name, dashboard_id)

    # -- import -------------------------------------------------------------

    def import_dashboard(self, zip_path: Path) -> bool:
        """Import a dashboard zip with overwrite=true. Returns True on success."""
        url = f"{self.base_url}/api/v1/dashboard/import/"

        if self.db_uri:
            patched = patch_zip_database_uri(zip_path, self.db_uri)
            files = {"formData": (zip_path.name, patched, "application/zip")}
        else:
            files = {"formData": (zip_path.name, open(zip_path, "rb"), "application/zip")}

        data: dict[str, str] = {"overwrite": "true"}

        try:
            resp = self.session.post(url, files=files, data=data,
                                     headers=self._csrf_headers())
        finally:
            files["formData"][1].close()

        if resp.ok:
            logger.info("Successfully imported '%s'", zip_path.name)
            return True

        logger.error("Failed to import '%s': %s %s",
                      zip_path.name, resp.status_code, resp.text)
        return False


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------

def sync_dashboards(
    superset_url: str,
    dashboards_dir: str,
    db_uri: str | None = None,
    force: bool = False,
    username: str | None = None,
    password: str | None = None,
    sec_username: str | None = None,
    sec_roles: str | None = None,
    sec_email: str | None = None,
) -> int:
    """Sync all .zip dashboard exports to Superset. Returns count of updates."""
    dashboards_path = Path(dashboards_dir).resolve()
    if not dashboards_path.is_dir():
        logger.error("Dashboards directory not found: %s", dashboards_path)
        sys.exit(1)

    zip_files = sorted(dashboards_path.glob("*.zip"))
    if not zip_files:
        logger.warning("No .zip files found in %s", dashboards_path)
        return 0

    client = SupersetClient(
        superset_url, db_uri=db_uri,
        username=username, password=password,
        sec_username=sec_username, sec_roles=sec_roles, sec_email=sec_email,
    )
    client.login()

    updated_count = 0
    for zip_path in zip_files:
        current_hash = compute_file_hash(zip_path)
        uuids = extract_dashboard_uuids(zip_path)

        if not uuids:
            logger.warning("No dashboard UUID found in '%s', skipping", zip_path.name)
            continue

        # Check remote hash tag for each dashboard in the zip
        needs_import = force
        if not force:
            for uuid in uuids:
                dashboard = client.find_dashboard_by_uuid(uuid)
                if dashboard is None:
                    logger.info("Dashboard %s not found in Superset, will import", uuid)
                    needs_import = True
                    break
                remote_hash = client.get_hash_tag(dashboard["id"])
                if remote_hash != current_hash:
                    logger.info(
                        "Hash mismatch for '%s' (remote=%s, local=%s)",
                        zip_path.name, remote_hash or "<none>", current_hash,
                    )
                    needs_import = True
                    break

        if not needs_import:
            logger.info("Up-to-date: '%s'", zip_path.name)
            continue

        # Import and tag
        if client.import_dashboard(zip_path):
            for uuid in uuids:
                dashboard = client.find_dashboard_by_uuid(uuid)
                if dashboard:
                    client.set_hash_tag(dashboard["id"], current_hash)
            updated_count += 1

    logger.info("Sync complete: %d dashboard(s) updated.", updated_count)
    return updated_count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sync Superset dashboards from local .zip exports.",
    )
    parser.add_argument(
        "--superset-url",
        default=os.environ.get("SUPERSET_URL", "http://localhost:8088"),
        help="Superset base URL (default: $SUPERSET_URL or http://localhost:8088)",
    )
    parser.add_argument(
        "--dashboards-dir",
        default=os.environ.get("DASHBOARDS_DIR", DEFAULT_DASHBOARDS_DIR),
        help="Directory containing .zip dashboard exports (default: $DASHBOARDS_DIR or /dashboards)",
    )
    parser.add_argument(
        "--db-uri",
        default=os.environ.get("ANALYTICS_DB_URI"),
        help="Override the sqlalchemy_uri in database configs, "
             "e.g. 'postgresql://tsdb:pwd@host:5432/analytics' (default: $ANALYTICS_DB_URI)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force import even if the hash has not changed",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    # Classic username/password auth
    auth_classic = parser.add_argument_group("classic auth (username/password)")
    auth_classic.add_argument(
        "--username",
        default=os.environ.get("SUPERSET_USERNAME"),
        help="Superset username (default: $SUPERSET_USERNAME)",
    )
    auth_classic.add_argument(
        "--password",
        default=os.environ.get("SUPERSET_PASSWORD"),
        help="Superset password (default: $SUPERSET_PASSWORD)",
    )

    # geOrchestra sec-header auth
    auth_georchestra = parser.add_argument_group(
        "geOrchestra auth (sec-headers)",
        "When --sec-username is set, sec-* headers are sent on every request "
        "and the login API is skipped.",
    )
    auth_georchestra.add_argument(
        "--sec-username",
        default=os.environ.get("SEC_USERNAME", "analytics_update"),
        help="geOrchestra sec-username header (default: $SEC_USERNAME or 'analytics_update')",
    )
    auth_georchestra.add_argument(
        "--sec-roles",
        default=os.environ.get("SEC_ROLES", "ROLE_SUPERSET_ADMIN"),
        help="geOrchestra sec-roles header (default: $SEC_ROLES or 'ROLE_SUPERSET_ADMIN')",
    )
    auth_georchestra.add_argument(
        "--sec-email",
        default=os.environ.get("SEC_EMAIL", "admin@example.com"),
        help="geOrchestra sec-email header (default: $SEC_EMAIL or 'admin@example.com')",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Classic auth takes priority when explicitly provided; otherwise default
    # to geOrchestra sec-header auth.
    use_classic = args.username is not None
    updated = sync_dashboards(
        superset_url=args.superset_url,
        dashboards_dir=args.dashboards_dir,
        db_uri=args.db_uri,
        force=args.force,
        username=args.username if use_classic else None,
        password=args.password if use_classic else None,
        sec_username=None if use_classic else args.sec_username,
        sec_roles=None if use_classic else args.sec_roles,
        sec_email=None if use_classic else args.sec_email,
    )
    sys.exit(0 if updated >= 0 else 1)


if __name__ == "__main__":
    main()
