# TwinAgents — Multi-Agent Workflow Automation (Cloud Run Hackathon)

TwinAgents is a lightweight two-agent system (Planner + Executor) deployed entirely on **Google Cloud Run**.  
Planner converts natural-language tasks into structured JSON plans and publishes them to **Pub/Sub**.  
Executor receives those via push, executes, and logs results.  

---

## 🚀 Live Demo
- **Planner URL:** https://planner-service-j36k2dhiga-ez.a.run.app  
- **Executor URL:** https://executor-service-j36k2dhiga-ez.a.run.app  

Try:
```bash
curl -s -X POST "https://planner-service-j36k2dhiga-ez.a.run.app/plan"   -H "Content-Type: application/json"   -d '{"text":"Summarize last meeting and email attendees"}' | jq
```

---

## 🧩 Architecture
1️⃣ Planner (FastAPI + Pub/Sub Publisher)  
2️⃣ Pub/Sub Topic → planner-to-executor  
3️⃣ Executor (FastAPI Subscriber)  
4️⃣ Logs → Cloud Logging  

---

## 🧠 Next Steps
- Integrate **Gemini / ADK** in Planner for real plan synthesis  
- Add Firestore + BigQuery for persistent logs  
- Secure Pub/Sub push with authenticated SA  

---

## 📦 Structure
```
twin-agents/
 ├─ planner/        # Planner FastAPI + Dockerfile  
 ├─ executor/       # Executor FastAPI + Dockerfile  
 ├─ twin-agents.http
 └─ README.md
```

Built by **Thulasiramsureshkumar (minutesactionnow)**  
For **Google Cloud Run Hackathon 2025**
