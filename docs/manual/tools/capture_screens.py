import httpx, sys
from playwright.sync_api import sync_playwright
U = "https://meetingnote-pro-amber.vercel.app"
OUT = "docs/manual/images/"
api = httpx.Client(base_url=U + "/api", timeout=120)
def tok(e): return api.post("/auth/login", json={"email": e, "password": "password1"}).json()["token"]
K, P = tok("kim@example.com"), tok("park@example.com")
H = {"Authorization": "Bearer " + K}
team = api.get("/teams", headers=H).json()[0]
# 이전 회의록 정리 (매뉴얼 화면을 깨끗하게)
for m in api.get(f"/teams/{team['id']}/meetings", headers=H).json():
    api.delete(f"/meetings/{m['id']}", headers=H)
for t in api.get(f"/teams/{team['id']}/todos", headers=H).json():
    api.delete(f"/todos/{t['id']}", headers=H)

def page(b, token=None, w=1280, h=860, path="/login.html"):
    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, locale="ko-KR")
    pg = ctx.new_page()
    pg.goto(U + "/login.html")
    pg.evaluate("localStorage.setItem('theme','light')")
    if token: pg.evaluate(f"localStorage.setItem('mnp_token','{token}')")
    else: pg.evaluate("localStorage.removeItem('mnp_token')")
    pg.goto(U + path); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
    return pg
def shot(pg, name, full=False):
    pg.wait_for_timeout(400); pg.screenshot(path=OUT + name + ".png", full_page=full); print("shot", name)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    # 1 로그인 · 회원가입
    pg = page(b); shot(pg, "01_login")
    pg.click("#toggle"); pg.fill("#email", "hong@example.com"); pg.fill("#uname", "홍길동"); pg.fill("#invite", team["invite_code"]); shot(pg, "02_signup")
    # 2 소속 팀 없음 (최선임)
    pc = page(b, tok("choi@example.com"), path="/team.html"); shot(pc, "03_team_onboard")
    # 3 회의록 목록 (빈 상태) → 새 회의록
    pg = page(b, K, path="/meetings.html"); shot(pg, "04_meetings_empty")
    pg.click("#newBtn"); shot(pg, "05_new_meeting")
    pg.set_input_files("#fileInput", "회의_녹음.wav"); pg.wait_for_timeout(1200); shot(pg, "06_uploading")
    pg.wait_for_function("document.getElementById('nBody').value.length>50", timeout=120000)
    shot(pg, "07_transcribed_title_required")
    pg.fill("#nTitle", "2차 스프린트 계획 회의"); pg.fill("#nWho", "김대리, 박과장, 이주임"); shot(pg, "08_ready_to_save")
    pg.click("#saveBtn"); pg.wait_for_selector("#newModal", state="hidden", timeout=120000)
    pg.wait_for_function("document.getElementById('list').innerText.includes('2차 스프린트')", timeout=20000); shot(pg, "09_meetings_list")
    mid = pg.locator("#list a").first.get_attribute("href").split("=")[1]
    # 4 상세 · 배정 · 댓글
    api.post(f"/meetings/{mid}/comments", json={"content": "외부 공유를 뺐으니 공유 링크 버튼은 이번에 넣지 않음"}, headers={"Authorization": "Bearer " + P})
    pd = page(b, K, path=f"/detail.html?id={mid}"); shot(pd, "10_detail", full=True)
    pd.locator('[data-open="who"]').first.click(); shot(pd, "11_detail_assign")
    pd.keyboard.press("Escape"); pd.click("#bodyToggle"); pd.fill("#cInput", "기한은 금요일로 확정했으면 함"); shot(pd, "12_detail_comment", full=True)
    # 5 칸반 - 하나는 진행, 하나는 기한 지남
    todos = api.get(f"/teams/{team['id']}/todos", headers=H).json()
    if todos:
        api.put(f"/todos/{todos[0]['id']}", json={"status": "DOING"}, headers=H)
    if len(todos) > 1:
        api.put(f"/todos/{todos[1]['id']}", json={"due_text": "어제"}, headers=H)
    pt = page(b, K, path="/todos.html"); pt.click("#tabAll"); pt.wait_for_timeout(800); shot(pt, "13_kanban_all")
    pt.click("#newBtn"); pt.fill("#nWhat", "회의실 예약 규칙 정리"); pt.fill("#nWhen", "이번 주 안"); shot(pt, "14_kanban_new")
    pt.keyboard.press("Escape")
    pm = page(b, K, w=390, h=844, path="/todos.html"); pm.click("#tabAll"); pm.wait_for_timeout(800)
    pm.locator("#board article").first.click(); shot(pm, "15_kanban_mobile_pick")
    # 6 팀 설정 · 내 정보
    pt2 = page(b, K, path="/team.html"); shot(pt2, "16_team", full=True)
    pp = page(b, K, path="/profile.html"); shot(pp, "17_profile", full=True)
    pdoc = page(b, None, path="/docs"); shot(pdoc, "18_swagger")
    b.close()
