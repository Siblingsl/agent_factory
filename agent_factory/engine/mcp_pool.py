from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(slots=True)
class MCPConnection:
    server_name: str
    endpoint: str
    healthy: bool = True
    last_checked: float = 0.0


class MCPPool:
    def __init__(self):
        self._connections: dict[str, MCPConnection] = {}

    def register(self, server_name: str, endpoint: str) -> None:
        self._connections[server_name] = MCPConnection(
            server_name=server_name,
            endpoint=endpoint,
            healthy=True,
            last_checked=time.time(),
        )

    def get(self, server_name: str) -> MCPConnection | None:
        return self._connections.get(server_name)

    def list(self) -> list[MCPConnection]:
        return list(self._connections.values())

    async def health_check(self) -> dict[str, bool]:
        result = {}
        now = time.time()
        for conn in self._connections.values():
            conn.last_checked = now
            result[conn.server_name] = conn.healthy
        return result
