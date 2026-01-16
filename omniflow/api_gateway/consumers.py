import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from omniflow.core.orchestration.supervisor_graph import run_supervisor
from omniflow.utils.logging import get_logger

from django.db import connections
from django.db import close_old_connections

from omniflow.shipstream.models import Shipment

logger = get_logger(__name__)


class QueryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        logger.info("WebSocket client connected")

    async def receive(self, text_data=None):
        payload = json.loads(text_data)

        query = payload.get("query")
        user_email = payload.get("user_email")
        request_id = payload.get("request_id") or str(uuid.uuid4())

        logger.info(f"WebSocket request - User: {user_email}, Query: {query[:50] if query else 'None'}...")

        if not query or not user_email:
            await self.send(json.dumps({
                "type": "error",
                "request_id": request_id,
                "error": "query and user_email are required",
            }))
            return

        try:
            await self._log_db_health(request_id=request_id)

            await self.send(json.dumps({
                "type": "started",
                "request_id": request_id,
            }))

            result = await self._run_supervisor_safe(query=query, user_email=user_email)
            logger.info("WebSocket request completed successfully")

            trace = (result or {}).get("decision_trace") or []
            for step in trace:
                await self.send(json.dumps({
                    "type": "trace_step",
                    "request_id": request_id,
                    "step": step,
                }))

            await self.send(json.dumps({
                "type": "final",
                "request_id": request_id,
                "response": result,
            }))
        except Exception as e:
            logger.error(f"WebSocket request failed: {e}")
            await self.send(json.dumps({
                "type": "error",
                "request_id": request_id,
                "error": str(e),
            }))

    @database_sync_to_async
    def _run_supervisor_safe(self, query: str, user_email: str):
        # Ensure stale DB connections in long-running Daphne workers don't interfere.
        close_old_connections()
        return run_supervisor(query=query, user_email=user_email)

    @database_sync_to_async
    def _log_db_health(self, request_id: str):
        try:
            db_name = connections["shipstream"].settings_dict.get("NAME")
        except Exception:
            db_name = None
        try:
            count = Shipment.objects.using("shipstream").count()
        except Exception as e:
            logger.error(f"WS db_health failed request_id={request_id} db={db_name}: {e}")
            return

        logger.info(f"WS db_health request_id={request_id} shipstream_db={db_name} shipment_count={count}")
