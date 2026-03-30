from __future__ import annotations

from dataclasses import dataclass, field
import asyncio
import time
import uuid


@dataclass(slots=True)
class BulletinPost:
    post_id: str
    round_number: int
    author_slug: str
    author_name: str
    content: str
    position: str
    addressed_to: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.8
    key_claims: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        round_number: int,
        author_slug: str,
        author_name: str,
        content: str,
        position: str,
        key_claims: list[str],
    ) -> "BulletinPost":
        return cls(
            post_id=str(uuid.uuid4()),
            round_number=round_number,
            author_slug=author_slug,
            author_name=author_name,
            content=content,
            position=position,
            key_claims=key_claims,
        )


class BulletinBoard:
    def __init__(self):
        self._posts: list[BulletinPost] = []
        self._lock = asyncio.Lock()

    async def publish(self, post: BulletinPost) -> None:
        async with self._lock:
            self._posts.append(post)

    def read_all(self) -> list[BulletinPost]:
        return list(self._posts)

    def read_round(self, round_number: int) -> list[BulletinPost]:
        return [p for p in self._posts if p.round_number == round_number]

    def read_by_round_excluding(self, round_number: int, exclude_slug: str) -> list[BulletinPost]:
        return [
            p
            for p in self._posts
            if p.round_number == round_number and p.author_slug != exclude_slug
        ]
