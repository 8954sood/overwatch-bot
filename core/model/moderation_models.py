from dataclasses import dataclass
from typing import Optional

@dataclass
class ModerationLog:
    case_id: int
    user_id: int
    moderator_id: int
    action: str
    reason: Optional[str]
    count: Optional[int]
    created_at: str
