"""Product image proxy and media serving endpoints.

Provides Cloudflare-free access to product images for WooCommerce and third-party consumers.
Serves cached local media or downloads on-the-fly via residential proxy/cookies if available.
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.api.dependencies import verify_api_key

router = APIRouter(tags=["Media & Images"])

# Placeholder SVG to return when upstream blocks image download, so WooCommerce never sees HTTP 403
FALLBACK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#f1f5f9"/>
  <g fill="#94a3b8" transform="translate(100, 100)">
    <path d="M100 20 C55.8 20 20 55.8 20 100 C20 144.2 55.8 180 100 180 C144.2 180 180 144.2 180 100 C180 55.8 144.2 20 100 20 Z M100 160 C66.9 160 40 133.1 40 100 C40 66.9 66.9 40 100 40 C133.1 40 160 66.9 160 100 C160 133.1 133.1 160 100 160 Z"/>
    <circle cx="100" cy="100" r="30"/>
    <path d="M80 85 L130 100 L80 115 Z" fill="#64748b"/>
  </g>
  <text x="200" y="310" font-family="sans-serif" font-size="14" fill="#64748b" text-anchor="middle">Audiovideo.lt Product Image</text>
  <text x="200" y="330" font-family="sans-serif" font-size="11" fill="#94a3b8" text-anchor="middle">Cached on Railway</text>
</svg>"""


def get_media_root() -> Path:
    """Return resolved absolute path to media directory."""
    root = Path(settings.MEDIA_DIR)
    if not root.is_absolute():
        # Relative to scraper directory
        root = Path(__file__).resolve().parent.parent.parent.parent / settings.MEDIA_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def rewrite_image_url(url: str, base_url: Optional[str] = None) -> str:
    """Rewrite remote audiovideo.lt image URL to point to our local media proxy."""
    if not url:
        return url
    base = (base_url or settings.BASE_URL).rstrip("/")
    if "audiovideo.lt/media/catalog/product" in url:
        # Extract relative path after /media/catalog/product/
        parts = url.split("media/catalog/product/")
        if len(parts) == 2:
            rel_path = parts[1].lstrip("/")
            return f"{base}/media/catalog/product/{rel_path}"
    elif url.startswith("/media/catalog/product/"):
        rel_path = url.replace("/media/catalog/product/", "").lstrip("/")
        return f"{base}/media/catalog/product/{rel_path}"
    return url


@router.get(
    "/media/catalog/product/{file_path:path}",
    summary="Serve or proxy product image without Cloudflare 403 block",
    description="Serves cached product images directly to WooCommerce and browsers. Automatically fetches and caches missing images.",
)
async def serve_product_image(file_path: str):
    """
    Public image endpoint.
    Serves images without Cloudflare blocks, ensuring WooCommerce image imports succeed.
    """
    # Sanitize path to prevent directory traversal
    clean_path = os.path.normpath(file_path).lstrip("/\\")
    if clean_path.startswith("..") or ".." in clean_path.split(os.sep):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path")

    media_root = get_media_root()
    local_file = media_root / "catalog" / "product" / clean_path

    # 1. Return cached file if it exists and is non-empty
    if local_file.exists() and local_file.stat().st_size > 0:
        mime, _ = mimetypes.guess_type(str(local_file))
        return FileResponse(
            str(local_file),
            media_type=mime or "image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000, immutable"}
        )

    # 2. Attempt on-the-fly fetch from remote host
    remote_url = f"https://www.audiovideo.lt/media/catalog/product/{clean_path}"
    headers = {
        "User-Agent": settings.SCRAPER_USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://www.audiovideo.lt/",
    }
    if settings.SCRAPER_COOKIES:
        headers["Cookie"] = settings.SCRAPER_COOKIES

    client_kwargs = {"timeout": 15.0, "follow_redirects": True}
    if settings.RESIDENTIAL_PROXY_URL:
        client_kwargs["proxy"] = settings.RESIDENTIAL_PROXY_URL

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(remote_url, headers=headers)
            if resp.status_code == 200 and len(resp.content) > 100:
                # Save to disk cache
                local_file.parent.mkdir(parents=True, exist_ok=True)
                local_file.write_bytes(resp.content)
                content_type = resp.headers.get("content-type", "image/jpeg")
                return Response(
                    content=resp.content,
                    media_type=content_type,
                    headers={"Cache-Control": "public, max-age=31536000"}
                )
    except Exception:
        pass

    # 3. Fallback: Return standard placeholder SVG with HTTP 200 so WooCommerce import does NOT fail
    return Response(
        content=FALLBACK_SVG.encode("utf-8"),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"}
    )


@router.post(
    "/api/v1/media/upload",
    summary="Upload image directly to media store",
    description="Allows uploading images directly to the media store under /media/catalog/product/.",
)
async def upload_product_image(
    file: UploadFile = File(..., description="Image file (JPEG/PNG/WEBP)"),
    target_path: str = Form(..., description="Target path e.g. '8/9/890sp25a_2.jpg'"),
    _: str = Depends(verify_api_key),
):
    """Upload product image file into media store."""
    clean_path = os.path.normpath(target_path).lstrip("/\\")
    if clean_path.startswith("..") or ".." in clean_path.split(os.sep):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target path")

    media_root = get_media_root()
    dest = media_root / "catalog" / "product" / clean_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    dest.write_bytes(content)

    return {
        "success": True,
        "message": f"Image uploaded successfully: {clean_path}",
        "data": {
            "path": clean_path,
            "url": f"{settings.BASE_URL.rstrip('/')}/media/catalog/product/{clean_path}",
            "size_bytes": len(content)
        }
    }
