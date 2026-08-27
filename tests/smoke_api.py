"""冒烟测试：验证后端 API 基本链路（不依赖真实 fal 生成）。

运行：uv run python tests/smoke_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
TIMEOUT = httpx.Timeout(30.0, connect=5.0)


def main() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool, extra: str = "") -> None:
        status = "PASS" if cond else "FAIL"
        print(f"[{status}] {name} {extra}")
        if not cond:
            failures.append(name)

    r = httpx.get(f"{BASE}/api/health", timeout=TIMEOUT)
    check("health", r.status_code == 200, f"-> {r.json()}")

    r = httpx.get(f"{BASE}/api/voices", params={"page_size": 5}, timeout=TIMEOUT)
    data = r.json()
    check("voices list", r.status_code == 200 and data["total"] > 500 and len(data["list"]) == 5,
          f"-> total={data.get('total')}")

    # 搜索
    r = httpx.get(f"{BASE}/api/voices", params={"search": "女", "page_size": 20}, timeout=TIMEOUT)
    d = r.json()
    check("voices search", r.status_code == 200 and d["total"] > 0, f"-> total={d.get('total')}")

    # 只看星标（先收藏一个）
    vid = d["list"][0]["id"]
    r = httpx.post(f"{BASE}/api/voices/{vid}/favorite", timeout=TIMEOUT)
    check("favorite", r.status_code == 200 and r.json()["is_favorite"] is True)
    r = httpx.get(f"{BASE}/api/voices", params={"only_favorite": "true"}, timeout=TIMEOUT)
    fav = r.json()
    check("only_favorite filter", r.status_code == 200 and fav["total"] >= 1, f"-> total={fav.get('total')}")
    r = httpx.delete(f"{BASE}/api/voices/{vid}/favorite", timeout=TIMEOUT)
    check("unfavorite", r.status_code == 200 and r.json()["is_favorite"] is False)

    # 最近使用
    r = httpx.get(f"{BASE}/api/voices", params={"recent": 5}, timeout=TIMEOUT)
    check("recent voices", r.status_code == 200, f"-> len={len(r.json().get('list', []))}")

    # 音色试听音频
    r = httpx.get(f"{BASE}/api/voices/{vid}/audio", timeout=TIMEOUT)
    check("voice audio stream", r.status_code == 200 and r.headers.get("content-type", "").startswith("audio"),
          f"-> {r.status_code} {r.headers.get('content-type')}")

    # 上传自定义音色
    wav = bytes.fromhex("52494646" + "00" * 40 + "57415645")
    files = {"file": ("test.wav", wav, "audio/wav")}
    r = httpx.post(f"{BASE}/api/voices", data={"name": "冒烟测试音色"}, files=files, timeout=TIMEOUT)
    check("upload custom voice", r.status_code == 201, f"-> {r.status_code} {r.text[:120]}")
    if r.status_code == 201:
        custom_id = r.json()["id"]
        r = httpx.get(f"{BASE}/api/voices/{custom_id}/audio", timeout=TIMEOUT)
        check("custom voice audio", r.status_code == 200, f"-> {r.status_code}")

    # 任务创建（无 FAL_KEY 或网络不可用时应 gracefully failed，不崩溃）
    r = httpx.post(f"{BASE}/api/tasks", json={"voice_id": vid, "text": "这是一段测试文字，用来验证语音合成任务。123456"}, timeout=TIMEOUT)
    check("create task", r.status_code == 201, f"-> {r.status_code}")
    if r.status_code == 201:
        task_id = r.json()["id"]
        import time

        time.sleep(3)
        r = httpx.get(f"{BASE}/api/tasks/{task_id}", timeout=TIMEOUT)
        task = r.json()
        check("task detail", r.status_code == 200, f"-> status={task.get('status')}")
        r = httpx.get(f"{BASE}/api/tasks", timeout=TIMEOUT)
        tl = r.json()
        check("task list", r.status_code == 200 and tl["total"] >= 1, f"-> total={tl.get('total')}")

    # 404 兜底
    r = httpx.get(f"{BASE}/api/voices/999999", timeout=TIMEOUT)
    check("404 fallback", r.status_code == 404)

    print()
    if failures:
        print(f"FAILED: {len(failures)} 项未通过: {failures}")
        return 1
    print("ALL SMOKE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
