"""Google Drive — выдача PDF программ туров.

Бот не пользуется именами файлов — берёт `pdf_file_id` из метаданных тура.
"""
from __future__ import annotations

import asyncio
import io
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.config.settings import get_settings

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_drive_service = None


def _get_service():
    global _drive_service
    if _drive_service is None:
        settings = get_settings()
        creds = Credentials.from_service_account_info(
            settings.google_service_account, scopes=SCOPES
        )
        _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _drive_service


async def fetch_pdf(file_id: str) -> bytes:
    """Скачивает PDF из Drive по ID файла."""
    return await asyncio.to_thread(_fetch_pdf_sync, file_id)


def _fetch_pdf_sync(file_id: str) -> bytes:
    service = _get_service()
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return buf.read()
