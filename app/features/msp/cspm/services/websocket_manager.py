"""
WebSocket Broadcast Manager for CSPM Scans

Manages WebSocket connections and broadcasts scan progress updates from
webhook endpoints to connected clients.
"""

import asyncio
from collections import defaultdict
from typing import Any, Dict, Set
import structlog

from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class WebSocketManager:
    """
    Singleton manager for WebSocket connections to scan progress streams.

    Bridges webhook progress updates (from PowerShell) to WebSocket clients
    for real-time UI updates.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._initialized = True

        logger.info("WebSocket manager initialized")

    async def connect(self, scan_id: str, websocket: WebSocket) -> None:
        """
        Register a new WebSocket connection for a scan.

        Args:
            scan_id: Scan UUID
            websocket: FastAPI WebSocket connection
        """
        async with self._lock:
            self._connections[scan_id].add(websocket)

        logger.info(
            "WebSocket connected",
            scan_id=scan_id,
            total_connections=len(self._connections[scan_id])
        )

    async def disconnect(self, scan_id: str, websocket: WebSocket) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            scan_id: Scan UUID
            websocket: FastAPI WebSocket connection
        """
        async with self._lock:
            self._connections[scan_id].discard(websocket)

            # Clean up empty connection sets
            if not self._connections[scan_id]:
                del self._connections[scan_id]

        logger.info(
            "WebSocket disconnected",
            scan_id=scan_id,
            remaining_connections=len(self._connections.get(scan_id, set()))
        )

    async def broadcast(self, scan_id: str, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected WebSocket clients for a scan.

        Args:
            scan_id: Scan UUID
            message: JSON-serializable message dictionary
        """
        async with self._lock:
            connections = list(self._connections.get(scan_id, set()))

        if not connections:
            logger.debug("No WebSocket connections to broadcast to", scan_id=scan_id)
            return

        # Track failed connections to remove them
        failed_connections = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send WebSocket message",
                    scan_id=scan_id,
                    error=str(e)
                )
                failed_connections.append(websocket)

        # Remove failed connections
        if failed_connections:
            async with self._lock:
                for websocket in failed_connections:
                    self._connections[scan_id].discard(websocket)

        logger.debug(
            "Broadcast sent to WebSocket clients",
            scan_id=scan_id,
            connections=len(connections) - len(failed_connections),
            failed=len(failed_connections)
        )

    def get_connection_count(self, scan_id: str) -> int:
        """
        Get the number of active WebSocket connections for a scan.

        Args:
            scan_id: Scan UUID

        Returns:
            Number of active connections
        """
        return len(self._connections.get(scan_id, set()))


# Global singleton instance
websocket_manager = WebSocketManager()
