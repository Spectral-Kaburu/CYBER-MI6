"""GET /api/stats: the dashboard's headline numbers."""

from fastapi import APIRouter, Depends

from backend import storage
from backend.db import Database
from backend.deps import get_db
from backend.models import Stats

router = APIRouter()


@router.get("/stats", response_model=Stats)
def get_stats(db: Database = Depends(get_db)):
    return storage.stats(db)
