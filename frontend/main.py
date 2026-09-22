"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import json
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

_A2UI_MIME = "application/json+a2ui"
_A2UI_KEYS = ("beginRendering", "surfaceUpdate", "dataModelUpdate", "deleteSurface", "surfaceId", "components")
_TAG_RE = re.compile(r"</?(?:a2a_datapart_json|a2ui-json)>")

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card


def _parse_a2ui_from_text(text: str) -> tuple[str, list[dict]]:
    """Parse text for A2UI JSON structures. Returns (clean_prose, list_of_a2ui_messages)."""
    if not text or not any(k in text for k in ("<a2ui-json>", "<a2a_datapart_json>", "surfaceId", "surfaceUpdate", "beginRendering", "components")):
        return text, []

    tag_matches = list(re.finditer(r"<(a2ui-json|a2a_datapart_json)>(.*?)</\1>", text, re.DOTALL))
    raw_payloads = []
    clean_text = text

    if tag_matches:
        for match in tag_matches:
            tag_content = match.group(2).strip()
            try:
                raw_payloads.append(json.loads(tag_content))
                clean_text = clean_text.replace(match.group(0), "")
            except Exception:
                pass
    else:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[-1]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
        stripped = _TAG_RE.sub("", stripped).strip()
        try:
            val = json.loads(stripped)
            if isinstance(val, (dict, list)):
                raw_payloads.append(val)
                clean_text = ""
        except Exception:
            pass

    normalized_messages: list[dict] = []
    for item in raw_payloads:
        items = item if isinstance(item, list) else [item]
        for obj in items:
            if not isinstance(obj, dict):
                continue
            if "data" in obj and isinstance(obj["data"], dict) and any(k in obj["data"] for k in _A2UI_KEYS):
                obj = obj["data"]

            if any(k in obj for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate", "deleteSurface")):
                normalized_messages.append(obj)
            elif "components" in obj or "surfaceId" in obj:
                components = obj.get("components", [])
                surface_id = obj.get("surfaceId", "surface1")
                root_id = obj.get("root") or (components[0].get("id") if components else None)
                if root_id:
                    normalized_messages.append({"beginRendering": {"root": root_id, "surfaceId": surface_id}})
                normalized_messages.append({"surfaceUpdate": {"surfaceId": surface_id, "components": components}})

    return clean_text.strip(), normalized_messages


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI."""
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            clean_prose, a2ui_msgs = _parse_a2ui_from_text(root.text)
            if clean_prose:
                out.append({"kind": "text", "text": clean_prose})
            for msg in a2ui_msgs:
                out.append({"kind": "a2ui", "data": msg})
        elif getattr(root, "data", None) is not None:
            data_val = root.data
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME or (isinstance(data_val, dict) and any(k in data_val for k in _A2UI_KEYS)):
                out.append({"kind": "a2ui", "data": data_val})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
