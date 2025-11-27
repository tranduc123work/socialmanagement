from ninja import Schema
from typing import Optional, List
from datetime import datetime


class PostCreateSchema(Schema):
    title: Optional[str] = None
    content: str
    post_type: str = 'text'
    media_urls: Optional[List[str]] = []
    link_url: Optional[str] = None
    hashtags: Optional[List[str]] = []
    page_ids: Optional[List[int]] = []


class PostSchema(Schema):
    id: int
    title: Optional[str]
    content: str
    status: str
    created_at: datetime
