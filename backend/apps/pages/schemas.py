from ninja import Schema
from typing import Optional
from datetime import datetime


class FacebookPageSchema(Schema):
    id: int
    facebook_page_id: str
    name: str
    category: Optional[str]
    picture_url: Optional[str]
    is_active: bool
    created_at: datetime
