"""Pytest test configuration and fixtures."""
import sys
import os
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add scraper directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.models import Base
from app.database.session import get_db
from app.main import app
from app.config import settings

# In-memory SQLite engine with StaticPool so all sessions share the same test database
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Provide a clean, isolated database session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Provide FastAPI test client wired to test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    """Header for authenticated API mutation requests."""
    return {"X-API-Key": settings.API_KEY}


@pytest.fixture
def sample_product_html() -> str:
    """Representative HTML fixture for an Audiovideo.lt product detail page."""
    return """
    <!DOCTYPE html>
    <html lang="lt">
    <head>
      <title>Hertz ML 700.3 Legend Vidutinių dažnių garsiakalbiai</title>
      <link rel="canonical" href="https://www.audiovideo.lt/hertz-ml-700-set-midrange" />
      <script type="application/ld+json">
      {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Hertz ML 700.3 Legend",
        "image": ["https://www.audiovideo.lt/media/catalog/product/h/e/hertz_ml700.jpg"],
        "description": "Aukščiausios klasės Mille Legend serijos vidutinių dažnių garsiakalbiai automobiliui.",
        "sku": "ML-700-3",
        "gtin13": "8018823113423",
        "brand": {
          "@type": "Brand",
          "name": "Hertz"
        },
        "offers": {
          "@type": "Offer",
          "url": "https://www.audiovideo.lt/hertz-ml-700-set-midrange",
          "priceCurrency": "EUR",
          "price": "349.00",
          "availability": "https://schema.org/InStock"
        }
      }
      </script>
    </head>
    <body>
      <h1 class="product-title">Hertz ML 700.3 Legend Vidutinių dažnių garsiakalbiai</h1>
      <div class="sku">Prekės kodas: ML-700-3</div>
      <div class="brand">Gamintojas: Hertz</div>
      <div class="price-wrapper">
        <span class="price">349,00 €</span>
      </div>
      <div class="availability">Sandėlyje yra</div>
      <div id="description">Aukščiausios klasės Mille Legend serijos vidutinių dažnių garsiakalbiai automobiliui.</div>
      
      <table class="table-specifications">
        <tbody>
          <tr><th>Maksimali galia</th><td>100 W</td></tr>
          <tr><th>Varža</th><td>4 Ohms</td></tr>
          <tr><th>Dažnių juosta</th><td>200 - 20000 Hz</td></tr>
        </tbody>
      </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_category_html() -> str:
    """Representative HTML fixture for an Audiovideo.lt category page."""
    return """
    <!DOCTYPE html>
    <html lang="lt">
    <head><title>Garso izoliacija - Audiovideo.lt</title></head>
    <body>
      <nav class="navigation category-menu">
        <ul>
          <li><a href="/automobiliu-garso-aparatura">Automobilių garso aparatūra</a>
            <ul>
              <li><a href="/automobiliu-garso-aparatura/garso-izoliacija">Garso izoliacija</a></li>
              <li><a href="/automobiliu-garso-aparatura/akustiniai-laidai">Akustiniai laidai</a></li>
            </ul>
          </li>
        </ul>
      </nav>
      
      <div class="products-grid">
        <div class="product-item">
          <a class="product-item-link" href="https://www.audiovideo.lt/vibrofiltr-profi-2-0mm-vibro-izoliacija">
            Vibrofiltr PROFI 2.0mm
          </a>
          <span class="price">4,50 €</span>
        </div>
        <div class="product-item">
          <a class="product-item-link" href="https://www.audiovideo.lt/sgm-techno-aliumast-alpha-2-izoliacija">
            SGM Techno Aliumast Alpha 2
          </a>
          <span class="price">5,20 €</span>
        </div>
      </div>

      <div class="pages pagination">
        <span class="current">1</span>
        <a href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=2">2</a>
        <a href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=3">3</a>
      </div>
    </body>
    </html>
    """
