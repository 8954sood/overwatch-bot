import json
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RoleButton:
    role_id: int
    label: str
    emoji: str
    style: str = 'secondary'


@dataclass
class RoleMessage:
    guild_id: int
    channel_id: int
    message_id: int
    content: str
    color: str
    buttons: List[RoleButton] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'RoleMessage':
        buttons_data = json.loads(row['role_buttons'])
        buttons = [RoleButton(**b) for b in buttons_data]
        return cls(
            guild_id=row['guild_id'],
            channel_id=row['channel_id'],
            message_id=row['message_id'],
            content=row['content'],
            color=row['color'],
            buttons=buttons
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'guild_id': self.guild_id,
            'channel_id': self.channel_id,
            'message_id': self.message_id,
            'content': self.content,
            'color': self.color,
            'role_buttons': json.dumps([b.__dict__ for b in self.buttons])
        }
