"""Scraping control and dispatch API endpoints."""
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.config import settings
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.job import JobScope, JobStatus, CrawlJobResponse, CrawlJobCreate
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.database.repositories.category_repo import CategoryRepository
from app.database.repositories.manufacturer_repo import ManufacturerRepository
from app.database.repositories.product_repo import ProductRepository
from app.extraction.products import extract_product_detail
from app.extraction.categories import (
    extract_category_tree,
    extract_listing_products,
    extract_category_description,
    extract_listing_product_items
)
from app.extraction.pagination import extract_pagination
from app.services.discovery import init_job_seeds
from app.services.coverage import get_overview_report
from app.services.dispatcher import JobDispatcher
from app.services.raw_store import raw_store
from app.services.job_runner import JobRunner

router = APIRouter(prefix="/scraping", tags=["Scraping Control"])


class URLListPayload(BaseModel):
    urls: List[str]

    model_config = {"json_schema_extra": {
        "example": {
            "urls": [
                "https://www.audiovideo.lt/gamintojai/hertz",
                "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison",
            ]
        },
        "examples": [
            {
                "urls": [
                    "https://www.audiovideo.lt/gamintojai/hertz",
                    "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison",
                ]
            }
        ]
    }}


class HTMLIngestPayload(BaseModel):
    url: str
    html: str
    final_url: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "url": "https://www.audiovideo.lt/prod-a.html",
            "html": "<!doctype html><html><head><title>Test product</title></head><body><h1>Test product</h1></body></html>",
            "final_url": "https://www.audiovideo.lt/prod-a.html",
        },
        "examples": [
            {
                "url": "https://www.audiovideo.lt/prod-a.html",
                "html": "<!doctype html><html><head><title>Test product</title></head><body><h1>Test product</h1></body></html>",
                "final_url": "https://www.audiovideo.lt/prod-a.html",
            }
        ]
    }}


class SnapshotAndScrapePayload(BaseModel):
    url: str = Field(..., description="Target Audiovideo.lt URL", json_schema_extra={"example": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/standartplast-stp-black-silver-bulk-pack.html"})
    html_content: Optional[str] = Field(None, description="Optional raw HTML content. If supplied, saves directly to disk snapshot and parses without network call.", json_schema_extra={"example": None})
    force_refresh: bool = Field(False, description="If True, bypasses local disk snapshot cache and performs new fetch/save.")

    model_config = {"json_schema_extra": {
        "example": {
            "url": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/standartplast-stp-black-silver-bulk-pack.html",
            "html_content": None,
            "force_refresh": False,
        },
        "examples": [
            {
                "url": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/standartplast-stp-black-silver-bulk-pack.html",
                "html_content": None,
                "force_refresh": False,
            }
        ]
    }}



@router.post("/start", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_scraping_job(
    background_tasks: BackgroundTasks,
    payload: CrawlJobCreate = CrawlJobCreate(),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Start a full or customized scraping job."""
    job = JobRepository.create_job(db, scope=payload.scope, config=payload.model_dump())
    init_job_seeds(db, job.id, custom_seeds=payload.seed_urls)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message="Scraping job queued and dispatched successfully",
        data={"job_id": job.id, "status": job.status, "scope": job.scope}
    )


@router.post("/start/category", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_category_scraping(
    background_tasks: BackgroundTasks,
    category_id: int = Query(...),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape a selected category."""
    cat = CategoryRepository.get_by_id(db, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    job = JobRepository.create_job(
        db, scope=JobScope.CATEGORY, config={"category_id": cat.id, "url": cat.source_url}
    )
    URLRepository.enqueue_url(db, job.id, cat.source_url)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Category scraping queued for '{cat.name}'",
        data={"job_id": job.id, "category_id": cat.id}
    )


@router.post("/start/manufacturer", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_manufacturer_scraping(
    background_tasks: BackgroundTasks,
    manufacturer_id: int = Query(...),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape a selected manufacturer."""
    man = ManufacturerRepository.get_by_id(db, manufacturer_id)
    if not man or not man.source_url:
        raise HTTPException(status_code=404, detail="Manufacturer not found or missing source URL")

    job = JobRepository.create_job(
        db, scope=JobScope.MANUFACTURER, config={"manufacturer_id": man.id, "url": man.source_url}
    )
    URLRepository.enqueue_url(db, job.id, man.source_url)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Manufacturer scraping queued for '{man.name}'",
        data={"job_id": job.id, "manufacturer_id": man.id}
    )


@router.post("/start/search", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_search_scraping(
    background_tasks: BackgroundTasks,
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape search results for a keyword."""
    encoded_q = quote_plus(query)
    search_url = f"https://www.audiovideo.lt/catalogsearch/result/?cat=0&q={encoded_q}"
    job = JobRepository.create_job(db, scope=JobScope.SEARCH, config={"query": query, "url": search_url})
    URLRepository.enqueue_url(db, job.id, search_url)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Search scraping queued for '{query}'",
        data={"job_id": job.id, "query": query}
    )


@router.post("/start/urls", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_urls_scraping(
    background_tasks: BackgroundTasks,
    payload: URLListPayload,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape a supplied list of URLs."""
    if not payload.urls:
        raise HTTPException(status_code=400, detail="URL list must not be empty")

    job = JobRepository.create_job(db, scope=JobScope.CUSTOM_URLS, config={"urls_count": len(payload.urls)})
    enqueued = URLRepository.enqueue_batch(db, job.id, payload.urls)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Custom URLs scraping queued ({enqueued} valid URLs enqueued)",
        data={"job_id": job.id, "enqueued_count": enqueued}
    )


@router.post("/ingest-html", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
def ingest_html_payload(
    payload: HTMLIngestPayload,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Ingest and cache raw HTML for a URL, then immediately parse it into the database."""
    raw_store.save(payload.url, payload.html, status_code=200, final_url=payload.final_url)
    job = JobRepository.create_job(db, scope=JobScope.CUSTOM_URLS, config={"source": "api_html_ingest"})
    crawl_url = URLRepository.enqueue_url(db, job.id, payload.url)
    db.commit()
    if crawl_url:
        JobRunner.process_url(db, job.id, crawl_url)
        db.commit()
    return APIResponse(
        success=True,
        message=f"Raw HTML snapshot saved and parsed for '{payload.url}'",
        data={"url": payload.url, "job_id": job.id}
    )


@router.post(
    "/snapshot-and-scrape",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Save HTML snapshot to disk and scrape immediately",
    description="Saves a raw HTML page snapshot to disk (data/raw/), then parses and extracts product or category data into the database. Pure backend execution."
)
def snapshot_and_scrape(
    payload: SnapshotAndScrapePayload,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    url = payload.url.strip()
    html = None
    effective_url = url
    is_cached = False
    raw_path = None

    # Step 1: Save HTML Page to Disk (Snapshot Store)
    if payload.html_content and payload.html_content.strip():
        html = payload.html_content.strip()
        raw_path = raw_store.save(url, html, status_code=200)
    else:
        # Check disk snapshot cache unless force_refresh
        if not payload.force_refresh and raw_store.has(url):
            cached = raw_store.load(url)
            if cached and cached.get("text"):
                html = cached["text"]
                effective_url = cached.get("final_url", url)
                is_cached = True
                raw_path = raw_store.root / raw_store._hash(url)
                raw_path = raw_path.with_suffix(".html")

        if not html:
            # Fetch from live network
            headers = {
                "User-Agent": settings.SCRAPER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "lt,en-US;q=0.7,en;q=0.3",
            }
            cookie_val = settings.SCRAPER_COOKIES
            env_p = Path(__file__).resolve().parent.parent.parent / ".env"
            if env_p.exists():
                for line in env_p.read_text(encoding="utf-8").splitlines():
                    if line.startswith("SCRAPER_COOKIES="):
                        c = line.split("=", 1)[1].strip()
                        if c:
                            cookie_val = c
                        break
            if cookie_val:
                headers["Cookie"] = cookie_val

            try:
                with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "NETWORK_FETCH_ERROR", "message": f"Failed to fetch {url}: {e}"}
                )

            is_cf = (
                resp.status_code == 403 or
                "challenges.cloudflare.com" in resp.text or
                "Cf-Mitigated" in resp.headers or
                "Luktelėkite..." in resp.text or
                "Just a moment..." in resp.text
            )
            if is_cf:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "ACCESS_RESTRICTED",
                        "message": "Cloudflare Bot Management challenge detected on live URL.",
                        "resolution": "Supply 'html_content' directly in this payload (Save HTML page as .html in browser, then pass content here), or configure SCRAPER_COOKIES."
                    }
                )

            html = resp.text
            effective_url = str(resp.url)
            raw_path = raw_store.save(url, html, status_code=resp.status_code, final_url=effective_url)

    # Step 2: Parse and Scrape the Saved HTML Page
    soup = BeautifulSoup(html, "lxml")
    has_product_form = bool(soup.select_one("form#product_addtocart_form, .product-view, .product-essential, .product-info-main"))
    has_category_listing = bool(soup.select_one(".products-grid, .category-products, .products-list"))

    is_product = (
        has_product_form or
        (url.endswith(".html") and not has_category_listing) or
        bool(soup.find("script", type="application/ld+json", string=lambda s: s and '"Product"' in s)) or
        bool(soup.find(attrs={"itemtype": lambda v: v and "Product" in v}))
    ) and not has_category_listing

    if is_product:
        prod_create = extract_product_detail(html, effective_url)
        if not prod_create or not prod_create.title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "PARSE_ERROR", "message": "Could not extract product details from saved HTML."}
            )

        prod, is_new = ProductRepository.upsert_product(db, prod_create)
        db.commit()
        db.refresh(prod)

        return APIResponse(
            success=True,
            message="HTML snapshot saved and product extracted successfully",
            data={
                "url": url,
                "effective_url": effective_url,
                "page_type": "product",
                "snapshot_saved": True,
                "snapshot_file": str(raw_path) if raw_path else None,
                "snapshot_size_bytes": len(html),
                "is_cached_replay": is_cached,
                "is_new_product": is_new,
                "product": {
                    "id": prod.id,
                    "title": prod.title,
                    "sku": prod.sku,
                    "ean": prod.ean,
                    "model": prod.model,
                    "brand": prod.brand_name,
                    "price": float(prod.price) if prod.price else None,
                    "currency": prod.currency,
                    "availability": prod.availability,
                    "in_stock": prod.in_stock,
                    "description": prod.description,
                    "canonical_url": prod.canonical_url,
                    "images_count": len(prod.images) if prod.images else 0,
                    "images": prod.images[:5] if prod.images else [],
                    "specifications_count": len(prod.specifications),
                    "specifications": [
                        {"label": s.label, "value": s.value, "unit": s.unit}
                        for s in prod.specifications
                    ]
                }
            }
        )
    else:
        # Category or listing page
        subcategories = extract_category_tree(soup, effective_url)
        for cat_create in subcategories:
            CategoryRepository.upsert_category(db, cat_create)

        curr_p, total_p, page_urls = extract_pagination(soup, effective_url)
        prod_urls = extract_listing_products(soup, effective_url)
        cat_desc = extract_category_description(soup)
        listing_items = extract_listing_product_items(soup, effective_url)

        # Ingest category and upsert products from listing
        from decimal import Decimal
        from app.schemas.category import CategoryCreate
        from app.schemas.product import ProductCreate

        cat_slug = effective_url.rstrip("/").split("/")[-1].split("?")[0]
        category_obj = (
            CategoryRepository.get_by_url(db, effective_url)
            or CategoryRepository.get_by_slug(db, cat_slug)
        )
        if not category_obj and cat_slug:
            h1 = soup.find("h1")
            cat_name = h1.get_text(strip=True) if h1 else cat_slug.replace("-", " ").title()
            cat_obj_create = CategoryCreate(name=cat_name, slug=cat_slug, source_url=effective_url)
            category_obj = CategoryRepository.upsert_category(db, cat_obj_create)

        cat_ids = [category_obj.id] if category_obj else []

        saved_products_count = 0
        for item in listing_items:
            if not item.get("url") or not item.get("title"):
                continue

            t_low = item["title"].lower()
            inferred_brand = None
            for b_cand in [
                "Bass Habit", "Hertz", "Audison", "Silent Coat", "Noise Protection",
                "SilenceWorld", "Boom", "STP", "Standartplast", "Alpine", "Pioneer", "JBL", "Focal"
            ]:
                if b_cand.lower() in t_low:
                    inferred_brand = b_cand
                    break
            if not inferred_brand:
                if "hertz" in effective_url.lower():
                    inferred_brand = "Hertz"
                elif "audison" in effective_url.lower():
                    inferred_brand = "Audison"
                elif "bass" in effective_url.lower():
                    inferred_brand = "Bass Habit"

            p_price = None
            if item.get("price") is not None:
                try:
                    p_price = Decimal(str(item["price"]))
                except Exception:
                    p_price = None

            prod_create = ProductCreate(
                canonical_url=item["url"],
                title=item["title"],
                price=p_price,
                currency=item.get("currency") or "EUR",
                images=[item["image"]] if item.get("image") else [],
                category_ids=cat_ids,
                brand_name=inferred_brand,
                in_stock=True,
                availability="in_stock",
                is_complete=False
            )
            ProductRepository.upsert_product(db, prod_create)
            saved_products_count += 1

        db.commit()

        return APIResponse(
            success=True,
            message="HTML snapshot saved and category/listing extracted successfully",
            data={
                "url": url,
                "effective_url": effective_url,
                "page_type": "category_listing",
                "snapshot_saved": True,
                "snapshot_file": str(raw_path) if raw_path else None,
                "snapshot_size_bytes": len(html),
                "is_cached_replay": is_cached,
                "category_description": cat_desc,
                "subcategories_found": len(subcategories),
                "products_found_count": len(listing_items) if listing_items else len(prod_urls),
                "products": listing_items,
                "product_links": prod_urls[:50],
                "pagination": {
                    "current_page": curr_p,
                    "total_pages": total_p,
                    "next_page_urls": page_urls
                }
            }
        )


@router.post(
    "/upload-and-scrape",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Upload saved HTML file directly and scrape",
    description="Select and upload a saved .html file directly from your computer with the file browser. Saves snapshot to disk and extracts all products into the database."
)
async def upload_and_scrape_file(
    file: UploadFile = File(..., description="Select the saved .html file from your computer"),
    url: str = Form("https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=bass+habit", description="The original Audiovideo.lt URL"),
    force_refresh: bool = Form(True, description="Force re-parsing if snapshot exists"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Direct file upload endpoint for browser-saved HTML files."""
    content_bytes = await file.read()
    html_content = content_bytes.decode("utf-8", errors="ignore")
    payload = SnapshotAndScrapePayload(
        url=url,
        html_content=html_content,
        force_refresh=force_refresh
    )
    return snapshot_and_scrape(payload=payload, db=db, _=_)


@router.post(
    "/batch-upload",
    response_model=APIResponse[dict],
    summary="Upload ZIP archive of saved HTML files for bulk ingestion",
    description="Upload a .zip file containing saved product and/or category .html files. Automatically extracts full descriptions, specifications tables, and gallery images in bulk.",
)
async def batch_upload_html_archive(
    file: UploadFile = File(..., description="ZIP archive containing saved .html files"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Bulk ingestion of multiple saved HTML pages from a ZIP file."""
    import zipfile
    import io

    archive_bytes = await file.read()
    if not zipfile.is_zipfile(io.BytesIO(archive_bytes)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ARCHIVE", "message": "Uploaded file is not a valid ZIP archive."}
        )

    processed_count = 0
    product_count = 0
    category_count = 0
    errors = []

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
        for fname in zf.namelist():
            if not fname.endswith(".html") and not fname.endswith(".htm"):
                continue
            try:
                html_bytes = zf.read(fname)
                html_text = html_bytes.decode("utf-8", errors="ignore")
                
                # Derive canonical url from HTML <link rel='canonical'> or filename
                soup_item = BeautifulSoup(html_text, "lxml")
                can_link = soup_item.find("link", rel=lambda r: r and "canonical" in r)
                item_url = can_link["href"].strip() if (can_link and can_link.get("href")) else f"https://www.audiovideo.lt/{Path(fname).stem}"
                
                payload = SnapshotAndScrapePayload(
                    url=item_url,
                    html_content=html_text,
                    force_refresh=True
                )
                res = snapshot_and_scrape(payload=payload, db=db, _=_)
                processed_count += 1
                if res.data.get("page_type") == "product":
                    product_count += 1
                else:
                    category_count += 1
            except Exception as e:
                errors.append(f"{fname}: {str(e)}")

    return APIResponse(
        success=True,
        message=f"Batch processed {processed_count} files ({product_count} products, {category_count} categories/listings)",
        data={
            "processed_total": processed_count,
            "products_saved": product_count,
            "categories_saved": category_count,
            "errors_count": len(errors),
            "errors": errors[:10]
        }
    )


@router.get(
    "/snapshots",
    response_model=APIResponse[List[dict]],
    summary="List all saved raw HTML page snapshots",
    description="Inspect all raw HTML pages saved on disk in the snapshot store."
)
def list_html_snapshots():
    """List all saved raw HTML page snapshots on disk."""
    items = raw_store.list_snapshots()
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} saved HTML snapshots",
        data=items
    )



@router.post("/pause/{job_id}", response_model=APIResponse[dict])
def pause_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Pause an active job."""
    job = JobRepository.update_status(db, job_id, JobStatus.PAUSED)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.commit()
    return APIResponse(success=True, message=f"Job {job_id} paused", data={"status": job.status})


@router.post("/resume/{job_id}", response_model=APIResponse[dict])
def resume_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Resume a paused job."""
    job = JobRepository.update_status(db, job_id, JobStatus.RUNNING)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.commit()
    return APIResponse(success=True, message=f"Job {job_id} resumed", data={"status": job.status})


@router.post("/cancel/{job_id}", response_model=APIResponse[dict])
def cancel_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Cancel a job."""
    job = JobRepository.update_status(db, job_id, JobStatus.CANCELLED)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.commit()
    return APIResponse(success=True, message=f"Job {job_id} cancelled", data={"status": job.status})


@router.get("/status", response_model=APIResponse[dict])
def get_current_scraping_status(db: Session = Depends(get_db)):
    """Get current scraping overview status."""
    overview = get_overview_report(db)
    return APIResponse(
        success=True,
        message="Current scraping status retrieved",
        data={
            "active_jobs": overview.active_jobs,
            "completed_jobs": overview.completed_jobs,
            "total_products_collected": overview.total_products,
            "processed_urls": overview.total_urls_processed,
            "failed_urls": overview.total_urls_failed,
            "inaccessible_urls": overview.total_urls_inaccessible
        }
    )


@router.get("/history", response_model=APIResponse[List[CrawlJobResponse]])
def get_scraping_history(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Get previous scraping runs and jobs."""
    jobs = JobRepository.list_jobs(db, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message="Scraping history retrieved",
        data=[CrawlJobResponse.model_validate(j) for j in jobs]
    )
