from fastapi import FastAPI, Request
import json, os
app = FastAPI()

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/run-task")
async def run_task(req: Request):
    body = await req.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        payload = {"raw": str(body)}

    # handle Pub/Sub push envelope
    if isinstance(payload, dict) and "message" in payload:
        import base64
        msg = payload["message"].get("data","")
        try:
            decoded = base64.b64decode(msg).decode("utf-8")
            plan = json.loads(decoded)
        except Exception:
            plan = {"error":"could not decode message", "raw": msg}
    else:
        plan = payload

    print("Executor received plan:", json.dumps(plan))
    results = []
    tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
    for t in tasks:
        results.append({"task_id": t.get("id"), "status": "done", "detail": t})
    return {"received_plan_id": plan.get("plan_id"), "results": results}
