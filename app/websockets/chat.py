"""
app/websockets/chat.py
-----------------------
WebSocket endpoint for a real-time chat room.

HTTP vs WebSocket:
  HTTP      → client asks, server answers, connection closes. One-way, request-response.
  WebSocket → connection stays open. Both sides can send messages at any time. Two-way.

Use cases for WebSockets: chat, live notifications, real-time dashboards, multiplayer games.
"""

# WebSocket         → represents an open WebSocket connection
# WebSocketDisconnect → raised when the client closes the connection
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


# No prefix here — WebSocket routes don't follow the /api/v1 convention
# tags=["WebSockets"] → groups under "WebSockets" in Swagger UI
router = APIRouter(tags=["WebSockets"])


class ConnectionManager:
    """
    Manages all currently connected WebSocket clients.

    When a user opens the WebSocket, we add them to active_connections.
    When they disconnect, we remove them.
    broadcast() sends a message to ALL connected clients.
    """

    def __init__(self):
        # active_connections → a list of all currently open WebSocket connections
        # Each WebSocket object represents one connected client
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # websocket.accept() → completes the WebSocket handshake.
        # You MUST call accept() before sending or receiving messages.
        # Without it, the connection is rejected.
        await websocket.accept()
        # Add this client to our list of active connections
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        # Remove the disconnected client from the list
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        # send_text() → sends a text message to ONE specific client
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """
        Send a message to ALL connected clients.
        Loops through every active connection and sends the message to each one.
        """
        for connection in self.active_connections:
            await connection.send_text(message)


# Create a single shared instance of ConnectionManager.
# All WebSocket connections use this same manager, so they can all communicate.
# If this were created inside the route function, each connection would have
# its own manager and couldn't see other connections.
manager = ConnectionManager()


# @router.websocket() → registers a WebSocket endpoint (not HTTP)
# "/ws/chat/{room_id}" → path parameter. ws://localhost:8000/ws/chat/room1
#   room_id → the name of the chat room (currently unused — all connections share one manager)
@router.websocket("/ws/chat/{room_id}")
async def websocket_chat(
    websocket: WebSocket,  # the WebSocket connection object
    room_id: str,          # extracted from the URL path
):
    """
    Connect to a chat room.
    - Send any text message to broadcast it to all room members.
    - Disconnect by closing the WebSocket connection.

    Test with websocat (install: brew install websocat):
      websocat ws://localhost:8000/ws/chat/room1
    """
    # Accept the connection and add to active connections
    await manager.connect(websocket)

    # Send a welcome message to just this new client
    await manager.send_personal_message(f"Welcome to room '{room_id}'!", websocket)

    # Announce to everyone that a new user joined
    await manager.broadcast(f"A new user joined room '{room_id}'")

    try:
        # while True → keep the connection open and listen for messages forever.
        # This loop runs until the client disconnects.
        while True:
            # receive_text() → waits (blocks) until the client sends a message.
            # Returns the message as a string.
            # await → this is async — while waiting, other connections can still run.
            data = await websocket.receive_text()

            # Broadcast the message to all connected clients (including the sender)
            await manager.broadcast(f"[{room_id}] {data}")

    except WebSocketDisconnect:
        # WebSocketDisconnect is raised when the client closes the connection
        # (closes the browser tab, loses internet, etc.)
        # We catch it to clean up gracefully instead of crashing.
        manager.disconnect(websocket)
        await manager.broadcast(f"A user left room '{room_id}'")
