from dataclasses import dataclass
from typing import Optional

@dataclass
class ShopItem:
    id: int
    item_type: str
    name: str
    price: int
    emoji: Optional[str]
    description: Optional[str]
    role_id: Optional[int]
    duration_days: Optional[int]

@dataclass
class InventoryItem:
    name: str
    count: int

@dataclass
class TemporaryRole:
    id: int
    user_id: int
    role_id: int
    expires_at: str