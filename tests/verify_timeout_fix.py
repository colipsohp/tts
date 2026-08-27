"""验证超时修复：创建任务并观察是否能撑过原 60s 阈值直至成功。"""

from __future__ import annotations

import sys
import time

import httpx

sys.path.insert(0, r"f:\4-Projects\TTS\backend")
from app.db.models import Voice  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from sqlalchemy import select  # noqa: E402

db = SessionLocal()
v = db.scalars(select(Voice).where(Voice.name.like("雷军%")).limit(1)).one()
db.close()

r = httpx.post(
    "http://127.0.0.1:8000/api/tasks",
    json={"voice_id": v.id, "text": "大家好，这是超时修复后的验证任务。"},
    timeout=30,
)
tid = r.json()["id"]
print(f"task {tid} created, watching up to 150s...", flush=True)

t0 = time.time()
for _ in range(30):
    time.sleep(5)
    elapsed = int(time.time() - t0)
    t = httpx.get(f"http://127.0.0.1:8000/api/tasks/{tid}", timeout=30).json()
    print(f"  [{elapsed}s] {t['status']}", flush=True)
    if t["status"] in ("succeeded", "failed"):
        print("  err:", (t.get("error_message") or "")[:200])
        print("  audio:", t.get("audio_url"))
        break
