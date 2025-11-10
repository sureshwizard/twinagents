from fastapi import FastAPI, Request
import json, uuid, time, os
from google.cloud import pubsub_v1

app = FastAPI()
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
topic_name = os.environ.get('PUBSUB_TOPIC','planner-to-executor')
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/plan")
async def plan_endpoint(req: Request):
    data = await req.json()
    text = data.get("text","")
    plan = {
        "plan_id": str(uuid.uuid4()),
        "intent": "auto_parsed_intent",
        "tasks": [
            {"id":"t1","type":"log","text": text}
        ],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    msg = json.dumps(plan).encode("utf-8")
    publisher.publish(topic_path, msg)
    return {"status":"planned","plan_id": plan["plan_id"], "published_to": topic_name}
