"""브라우저 확인 공통 도우미. E2E_URL 로 서버 주소를 바꿀 수 있다 (기본 http://127.0.0.1:8000)."""
import os, random, httpx
U=os.environ.get("E2E_URL","http://127.0.0.1:8000")
res=[]
def ok(label,cond):
    res.append(bool(cond)); print(("OK " if cond else "XX ")+label)
def seed():
    """owner 김대리 + member 박과장 · 이주임 팀."""
    r=random.randint(10000,99999); api=httpx.Client(base_url=U+"/api", timeout=90)
    def su(n,e):
        j=api.post("/auth/signup",json={"email":f"{e}{r}@ex.com","password":"password1","name":n}).json()
        return {"token":j["token"],"id":j["user"]["id"],"h":{"Authorization":"Bearer "+j["token"]},"email":f"{e}{r}@ex.com"}
    kim=su("김대리","kim"); team=api.post("/teams",json={"name":f"기획팀{r}"},headers=kim["h"]).json()
    park=su("박과장","park"); lee=su("이주임","lee")
    for u in (park,lee): api.post("/teams/join",json={"invite_code":team["invite_code"]},headers=u["h"])
    return api, team, kim, park, lee
def page_as(browser, user, path, width=1280):
    ctx=browser.new_context(viewport={"width":width,"height":900})
    pg=ctx.new_page(); errs=[]
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(U+"/login.html"); pg.evaluate(f"localStorage.setItem('mnp_token','{user['token']}')")
    pg.goto(U+path); pg.wait_for_load_state("networkidle")
    pg.errs=errs
    return pg
def no_hscroll(pg):
    return pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
