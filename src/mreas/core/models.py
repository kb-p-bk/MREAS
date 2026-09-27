from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Source:
    name: str
    author: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    origin: str = "moonreader"
    filename: Optional[str] = None

@dataclass
class Chunk:
    source_name: str
    highlight: Optional[str] = None
    user_note: Optional[str] = None
    tags: Optional[str] = None
    origin: str = "moonreader"
    mr_note_id: Optional[int] = None
    mr_timestamp: Optional[int] = None
    
    # Content hash is usually calculated right before inserting to db
    content_hash: Optional[str] = None
