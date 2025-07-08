from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    user_id: int
    display_name: str
    balance: int
    birthday: Optional[str] = None

@dataclass
class ActivityLog:
    user_id: int
    activity_date: str
    message_count: int
    voice_seconds: int

@dataclass
class ActivityStats:
    total_messages: int
    total_voice_minutes: int