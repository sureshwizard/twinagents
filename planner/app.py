# planner/app.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import uuid
import time
import logging

# Google clients
import google.auth
from google.cloud import pubsub_v1

# Firestore import is optional at runtime; import inside try for safer failure handling.
try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except Exception:
    firestore = None
    FIRESTORE_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("planner")

# ---------------------------------------------------------------------------
# App + CORS (restrict to your GitHub Pages origin and localhost for dev)
# ---------------------------------------------------------------------------
app = FastAPI(title="TwinAgents Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sureshwizard.github.io",  # tighten this as needed
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Google Cloud setup
# ---------------------------------------------------------------------------
# Use application default credentials in Cloud Run
credentials, default_project = google.auth.default()
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or default_project
PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "planner-to-executor")

publisher = pubsub_v1.PublisherClient()
topic_path = None
if PROJECT_ID:
    try:
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
    except Exception as e:
        log.warning("Could not form topic_path: %s", e)

# Firestore client (optional). Will set firestore_client=None if not available or DB missing.
firestore_client = None
if FIRESTORE_AVAILABLE:
    try:
        firestore_client = firestore.Client(project=PROJECT_ID)
        log.info("Initialized Firestore client for project %s", PROJECT_ID)
    except Exception as e:
        firestore_client = None
        log.warning("Firestore client init failed: %s", e)
else:
    log.info("google-cloud-firestore not available in this runtime (FIRESTORE_DISABLED)")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_plan(text: str) -> dict:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    plan_id = str(uuid.uuid4())
    plan = {
        "status": "planned",
        "plan_id": plan_id,
        "text": text,
        "timestamp": now,
    }
    return plan

def publish_to_pubsub(plan: dict) -> str:
    if not topic_path:
        raise RuntimeError("PUBSUB topic is not configured (topic_path missing).")
    data = json.dumps(plan).encode("utf-8")
    # publish returns a future — block briefly to get message id
    future = publisher.publish(topic_path, data)
    message_id = future.result(timeout=10)
    return message_id

def write_to_firestore(plan: dict) -> bool:
    if not firestore_client:
        raise RuntimeError("Firestore client not available or not initialized.")
    # Write to collection 'plans' with document name = plan_id
    coll = firestore_client.collection("plans")
    coll.document(plan["plan_id"]).set(plan)
    return True

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "project": PROJECT_ID, "topic": PUBSUB_TOPIC}

@app.post("/plan")
async def create_plan(req: Request):
    try:
        payload = await req.json()
    except Exception:
        payload = {}
    text = payload.get("text") or payload.get("task") or payload.get("message") or ""
    if not text:
        return {"status": "error", "message": "missing 'text' in request body"}

    plan = make_plan(text)

    # Attempt Firestore write (graceful)
    firestore_status = "disabled"
    try:
        if firestore_client:
            try:
                write_to_firestore(plan)
                firestore_status = "stored"
                log.info("Wrote plan %s to Firestore", plan["plan_id"])
            except Exception as e:
                firestore_status = "failed"
                log.exception("Firestore write failed: %s", e)
        else:
            firestore_status = "disabled"
    except Exception as ex:
        firestore_status = "failed"
        log.exception("Unexpected Firestore error: %s", ex)

    # Attempt publish to Pub/Sub
    published_to = "local-only-or-publish-failed"
    try:
        if topic_path:
            msg_id = publish_to_pubsub(plan)
            published_to = PUBSUB_TOPIC
            log.info("Published plan %s to Pub/Sub (msg id %s)", plan["plan_id"], msg_id)
        else:
            log.warning("Topic path not configured; skipping publish.")
    except Exception as e:
        log.exception("Publish to Pub/Sub failed: %s", e)
        published_to = "publish-failed"

    # Build response
    resp = {
        "status": plan.get("status"),
        "plan_id": plan.get("plan_id"),
        "firestore": firestore_status,
        "published_to": published_to,
        "timestamp": plan.get("timestamp"),
    }

    return resp

# ---------------------------------------------------------------------------
# Debug endpoint: direct run (optional) — keep for troubleshooting
# ---------------------------------------------------------------------------
@app.post("/_direct")
async def direct_run(payload: dict):
    """
    Simple debug: store payload to Firestore (if available) and return echo.
    Not used by normal flow, but handy for testing.
    """
    plan_id = payload.get("plan_id") or str(uuid.uuid4())
    payload["plan_id"] = plan_id
    payload.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    firestore_status = "disabled"
    try:
        if firestore_client:
            write_to_firestore(payload)
            firestore_status = "stored"
    except Exception as e:
        firestore_status = "failed"
        log.exception("Direct Firestore write failed: %s", e)

    return {"ok": True, "plan_id": plan_id, "firestore": firestore_status}
