"""API Dependencies: Database sessions and Authentication."""
from typing import Generator, Optional
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database.session import get_db

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="Enter API Key (default: test-operator-api-key-change-in-production)")
bearer_scheme = HTTPBearer(auto_error=False, description="Bearer token")


def verify_api_key(
    x_api_key: Optional[str] = Depends(api_key_header),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    raw_header_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Enforce API key authentication on administrative and mutation endpoints.
    Accepts X-API-Key header or Bearer token.
    Allows easy authorization via Swagger UI Authorize modal.
    """
    token = x_api_key or raw_header_key
    if not token and bearer_auth:
        token = bearer_auth.credentials

    if not token or token != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing API key. Provide X-API-Key header or authenticate in Swagger."
            }
        )
    return token
