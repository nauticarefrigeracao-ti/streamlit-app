"""
Persistência do banco via GitHub Releases.

Startup:  restore_from_github() — baixa o DB mais recente se diferente do local
Pós-ETL:  backup_to_github()    — cria Release e envia DB como asset

Requer env vars: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.config import DB_PATH, DB_ASSET_NAME, GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO

logger = logging.getLogger(__name__)

_GH_API = "https://api.github.com"
_GH_UPLOAD = "https://uploads.github.com"
_HEADERS = lambda token: {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
}


def restore_from_github() -> bool:
    """Baixa o DB do último Release se diferente do local. Retorna True se atualizou."""
    if not GITHUB_TOKEN or not GITHUB_OWNER or not GITHUB_REPO:
        logger.warning("GitHub não configurado — pulando restore")
        return False
    try:
        url = f"{_GH_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
        r = requests.get(url, headers=_HEADERS(GITHUB_TOKEN), params={"per_page": 5}, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Releases API: status {r.status_code}")
            return False

        asset_url = asset_size = release_tag = None
        for release in r.json():
            for asset in release.get("assets", []):
                if asset.get("name") == DB_ASSET_NAME:
                    asset_url = asset["browser_download_url"]
                    asset_size = asset.get("size", 0)
                    release_tag = release.get("tag_name", "")
                    break
            if asset_url:
                break

        if not asset_url:
            logger.info(f"Nenhum release com '{DB_ASSET_NAME}' encontrado")
            return False

        if DB_PATH.exists() and asset_size:
            local_size = DB_PATH.stat().st_size
            if local_size == asset_size:
                logger.info(f"DB local ({local_size:,} bytes) == release asset — sem alteração")
                return False
            logger.info(f"DB local ({local_size:,}b) != release ({asset_size:,}b [{release_tag}]) — baixando")
        else:
            logger.info(f"Baixando DB release asset ({asset_size:,} bytes [{release_tag}])")

        dl = requests.get(asset_url, timeout=120, stream=True)
        if dl.status_code != 200:
            logger.warning(f"Falha ao baixar asset: status {dl.status_code}")
            return False

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        with open(DB_PATH, "wb") as f:
            for chunk in dl.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)

        logger.info(f"DB restaurado: {total:,} bytes ({release_tag})")
        return True

    except Exception as e:
        logger.warning(f"Falha no restore: {e}")
        return False


def backup_to_github(reason: str = "") -> bool:
    """Cria um GitHub Release e envia o DB como asset. Retorna True se bem-sucedido."""
    if not GITHUB_TOKEN or not GITHUB_OWNER or not GITHUB_REPO:
        logger.warning("GitHub não configurado — pulando backup")
        return False

    if not DB_PATH.exists():
        logger.error(f"DB não encontrado em {DB_PATH}")
        return False

    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        tag = f"backup-{ts}"
        label = datetime.now().strftime("%d/%m/%Y %H:%M")
        body = f"Backup automático em {label}"
        if reason:
            body += f" — {reason}"

        rel_url = f"{_GH_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
        r = requests.post(
            rel_url,
            headers=_HEADERS(GITHUB_TOKEN),
            json={"tag_name": tag, "name": f"DB Backup {label}", "body": body,
                  "draft": False, "prerelease": False},
            timeout=30,
        )
        if r.status_code != 201:
            logger.error(f"Falha ao criar release: status {r.status_code} — {r.text[:200]}")
            return False

        release_id = r.json().get("id")
        if not release_id:
            logger.error("Release criada sem id")
            return False

        upload_url = (
            f"{_GH_UPLOAD}/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
            f"/releases/{release_id}/assets?name={DB_ASSET_NAME}"
        )
        with open(DB_PATH, "rb") as fh:
            upl = requests.post(
                upload_url,
                headers={**_HEADERS(GITHUB_TOKEN), "Content-Type": "application/x-sqlite3"},
                data=fh,
                timeout=120,
            )

        if upl.status_code == 201:
            size = DB_PATH.stat().st_size
            logger.info(f"DB backup enviado: {size:,} bytes (tag={tag})")
            return True

        logger.error(f"Falha ao enviar asset: status {upl.status_code} — {upl.text[:300]}")
        return False

    except Exception as e:
        logger.exception(f"Exceção no backup: {e}")
        return False
