"""브라우저 확인 전체 실행 - 서버를 먼저 띄운 뒤:

    uvicorn backend.main:app --port 8000
    python backend/tests/e2e/run_all.py          # 실제 녹취 받아쓰기까지: --wav

GEMINI_API_KEY 가 있어야 회의록 저장(세 갈래 구분)이 된다. pytest 와 달리 실제 서버와 Chrome 을 쓴다.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = ["login", "meetings", "detail", "todos", "team", "profile"]

failed = []
for p in PAGES:
    args = [sys.executable, os.path.join(HERE, f"e2e_{p}.py")]
    if p == "meetings" and "--wav" in sys.argv:
        args.append("--wav")
    print(f"\n== {p}")
    if subprocess.run(args, env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode != 0:
        failed.append(p)
print("\n실패: " + ", ".join(failed) if failed else "\n전체 통과")
sys.exit(1 if failed else 0)
