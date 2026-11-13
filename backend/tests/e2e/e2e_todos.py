import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2e_common import *
from playwright.sync_api import sync_playwright
api,team,kim,park,lee=seed(); tid=team["id"]
def add(what, who=None, due=""):
    return api.post(f"/teams/{tid}/todos",json={"what":what,"assignee_id":who,"due_text":due},headers=kim["h"]).json()
a=add("목록 화면 구현",kim["id"],"다음 주 금요일"); late=add("배포 키 이전",kim["id"],"어제"); un=add("사용자 인터뷰"); pk=add("박 업무",park["id"],"어제")
word=add("지난주 말한 일",kim["id"],"지난주"); today=add("오늘 할 일",kim["id"],"오늘")
def col(pg,key): return pg.locator(f'[data-col="{key}"]')
def status(i): return [t for t in api.get(f"/teams/{tid}/todos",headers=kim["h"]).json() if t["id"]==i][0]
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome")
    pg=page_as(b,kim,"/todos.html"); pg.wait_for_timeout(500)
    txt=pg.inner_text("#board")
    ok("E-01 내 할 일만", "목록 화면 구현" in txt and "박 업무" not in txt and "사용자 인터뷰" not in txt)
    pg.click("#tabAll"); pg.wait_for_timeout(500); txt=pg.inner_text("#board")
    ok("E-02 전체", all(w in txt for w in ("박 업무","사용자 인터뷰")) and "직접 등록" in txt)
    ok("E-09 담당자 미정 표시", "미정" in pg.locator(f'article[data-id="{un["id"]}"]').inner_text())
    ok("E-08 기한 지남 붉은 띠", "border-l-red-dot" in pg.locator(f'article[data-id="{late["id"]}"]').get_attribute("class"))
    ok("기한 정상은 붉은 띠 아님", "border-l-red-dot" not in pg.locator(f'article[data-id="{a["id"]}"]').get_attribute("class"))
    # modify-todo-due-date - 날짜 기준 지남 판정과 날짜 표시
    cls=lambda t: pg.locator(f'article[data-id="{t["id"]}"]').get_attribute("class")
    ok("오늘이 기한이면 붉은 띠 아님", "border-l-red-dot" not in cls(today))
    ok("날짜 없는 「지난주」 는 붉은 띠 아님", "border-l-red-dot" not in cls(word))
    chip=pg.locator(f'[data-act="due"][data-id="{a["id"]}"]').inner_text()
    import re as _re
    ok("기한 칩: 날짜 + 원래 글자", bool(_re.search(r"\d+월 \d+일 \([월화수목금토일]\)", chip)) and "다음 주 금요일" in chip)
    ok("날짜 못 정한 칩은 글자만", pg.locator(f'[data-act="due"][data-id="{word["id"]}"]').inner_text().strip()=="지난주")
    ok("isLate 날짜 비교", pg.evaluate("PAL.isLate({status:'OPEN',due_date:'2000-01-01'}) && !PAL.isLate({status:'DONE',due_date:'2000-01-01'}) && !PAL.isLate({status:'OPEN',due_text:'지난주'})"))
    # E-03/04 포인터 끌기
    card=pg.locator(f'article[data-id="{a["id"]}"]'); box=card.bounding_box(); tgt=col(pg,"DOING").bounding_box()
    puts=[]; pg.on("request", lambda q: puts.append(q.url) if q.method=="PUT" else None)
    pg.mouse.move(box["x"]+20, box["y"]+20); pg.mouse.down(); pg.mouse.move(box["x"]+40, box["y"]+40, steps=3)
    pg.mouse.move(tgt["x"]+tgt["width"]/2, tgt["y"]+tgt["height"]-15, steps=10)
    ok("E-03 끄는 중 점선 칸", "border-dashed" in col(pg,"DOING").inner_html() or "border-dashed" in (col(pg,"DOING").get_attribute("class") or ""))
    pg.mouse.up(); pg.wait_for_timeout(800)
    ok("E-04 놓으면 PUT 1번, DOING", len(puts)==1 and status(a["id"])["status"]=="DOING")
    ok("화면도 진행 칸으로", col(pg,"DOING").locator(f'article[data-id="{a["id"]}"]').count()==1)
    # E-04 실패하면 원래 칸으로
    pg.route("**/api/todos/*", lambda route: route.fulfill(status=500, content_type="application/json", body='{"code":"VALIDATION_ERROR","msg":"x"}') if route.request.method=="PUT" else route.continue_())
    card=pg.locator(f'article[data-id="{a["id"]}"]'); box=card.bounding_box(); tgt=col(pg,"DONE").bounding_box()
    pg.mouse.move(box["x"]+20, box["y"]+20); pg.mouse.down(); pg.mouse.move(box["x"]+40, box["y"]+40, steps=3)
    pg.mouse.move(tgt["x"]+tgt["width"]/2, tgt["y"]+tgt["height"]-15, steps=10); pg.mouse.up(); pg.wait_for_timeout(800)
    ok("E-04 PUT 실패 → 원래 칸(진행)으로", col(pg,"DOING").locator(f'article[data-id="{a["id"]}"]').count()==1 and status(a["id"])["status"]=="DOING")
    pg.unroute("**/api/todos/*")
    # E-06 담당자 배정
    pg.locator(f'[data-act="assign"][data-id="{un["id"]}"]').click(); pg.wait_for_timeout(200)
    pg.locator(f'[data-pick="{lee["id"]}"][data-id="{un["id"]}"]').click(); pg.wait_for_timeout(700)
    ok("E-06 담당자 배정", status(un["id"])["assignee_name"]=="이주임")
    # E-07 필터 (요청 없음)
    gets=[]; pg.on("request", lambda q: gets.append(q.url) if q.method=="GET" and "/api/" in q.url else None)
    pg.select_option("#fWho", label="박과장"); pg.wait_for_timeout(300)
    vis=pg.locator("#board article").count()
    ok("E-07 필터 화면에서만", vis==1 and not gets)
    pg.select_option("#fWho", index=0); pg.wait_for_timeout(200)
    # E-13 직접 등록
    pg.click("#newBtn"); ok("E-13 새 할 일 팝업", pg.is_visible("#newModal"))
    pg.fill("#nWhat","회의실 예약 규칙 정리"); pg.select_option("#nWho", label="이주임"); pg.fill("#nWhen","이번 주 안"); pg.click("#nSave"); pg.wait_for_timeout(800)
    ok("E-13 등록 → 대기 칸", "회의실 예약 규칙 정리" in col(pg,"OPEN").inner_text())
    # E-11 삭제 권한
    pp=page_as(b,lee,"/todos.html"); pp.click("#tabAll"); pp.wait_for_timeout(500)
    ok("E-11 권한 없는 카드 삭제 비활성", pp.locator(f'[data-act="del"][data-id="{pk["id"]}"]').is_disabled())
    pg.locator(f'[data-act="del"][data-id="{late["id"]}"]').click(); pg.wait_for_timeout(300)
    for btn in pg.locator("button", has_text="삭제").all():
        if btn.is_visible() and btn.get_attribute("data-act") is None: btn.click(); break
    pg.wait_for_timeout(700)
    ok("E-11 삭제", late["id"] not in [t["id"] for t in api.get(f"/teams/{tid}/todos",headers=kim["h"]).json()])
    # E-12 빈 상태
    e=page_as(b,park,"/todos.html"); api.delete(f"/todos/{pk['id']}",headers=park["h"]); e.reload(); e.wait_for_timeout(600)
    e.wait_for_selector("#empty", state="visible", timeout=15000)
    ok("E-12 빈 상태", e.is_visible("#empty"))
    # E-05 좁은 화면 눌러서 칸 고르기
    n=page_as(b,kim,"/todos.html",width=360); n.wait_for_timeout(500)
    ok("N-01 360px 가로 스크롤 없음", no_hscroll(n))
    n.locator(f'article[data-id="{a["id"]}"]').click(); n.wait_for_timeout(300)
    ok("E-05 칸 고르기 팝업", n.is_visible("#pickModal"))
    n.locator('[data-to="DONE"]').click(); n.wait_for_timeout(800)
    ok("E-05 완료로 이동 / E-10 완료 칸 유지", status(a["id"])["status"]=="DONE" and col(n,"DONE").locator(f'article[data-id="{a["id"]}"]').count()==1)
    ok("JS 오류 없음", not (pg.errs or pp.errs or e.errs or n.errs))
    b.close()
print(f"{sum(res)}/{len(res)}"); sys.exit(0 if all(res) else 1)
