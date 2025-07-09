from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class QnaChannel:
    channel_id: int
    guild_id: int
    pinned_message_id: Optional[int]
    pinned_title: Optional[str]
    pinned_content: Optional[str]

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'QnaChannel':
        return cls(
            channel_id=row['channel_id'],
            guild_id=row['guild_id'],
            pinned_message_id=row.get('pinned_message_id'),
            pinned_title=row.get('pinned_title'),
            pinned_content=row.get('pinned_content')
        )
