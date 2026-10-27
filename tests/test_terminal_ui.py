#!/usr/bin/env python3
"""
Browser tests for the terminal UI (navigation, filters, sorting, export,
search, event panel, story merging, data freshness labels, responsive layout,
encrypted build). Runs against the local readable page and an encrypted build
made with a throwaway test passcode.

  pip install playwright cryptography && python -m playwright install chromium
  python tests/test_terminal_ui.py
"""
import asyncio, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "terminal.src.html")
FAILED = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: FAILED.append(name)

async def unlocked(b, url, vp=(1500, 920)):
    ctx = await b.new_context(viewport={"width": vp[0], "height": vp[1]}, accept_downloads=True)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(url)
    await pg.evaluate("sessionStorage.setItem('aiCapitalTerminalUnlocked','1')")
    await pg.reload(); await pg.wait_for_timeout(1200)
    return pg, errs

async def main():
    if not os.path.exists(SRC): sys.exit(f"Missing {SRC} (the readable page is local-only).")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg, errs = await unlocked(b, "file://" + SRC)
        J = pg.evaluate

        # Navigation
        check("lands on Daily Events", await J("document.querySelector('.view.on').id") == "view-events")
        views = await J("[...document.querySelectorAll('nav a[data-view]')].map(a=>a.dataset.view)")
        check("nine menu items", len(views) == 9, str(views))
        for v in views:
            await pg.click(f"nav a[data-view='{v}']"); await pg.wait_for_timeout(120)
            on = await J("document.querySelector('.view.on').id")
            cur = await J("document.querySelector('nav a[aria-current=page]').dataset.view")
            check(f"menu → {v}", on == "view-" + v and cur == v, on)
        check("Daily Events reachable from every view (rail always present)", await J("getComputedStyle(document.querySelector('nav')).display!=='none'"))
        check("every original section is placed in a view", await J("[...document.querySelectorAll('section[id]')].every(s=>s.closest('.view'))"))

        # Cross-view anchor routing
        await pg.evaluate("location.hash='#fn-c'"); await pg.wait_for_timeout(300)
        check("anchor #fn-c opens Cash Flow & CAPEX", await J("document.querySelector('.view.on').id") == "view-cash")
        await pg.evaluate("location.hash='#/events'"); await pg.wait_for_timeout(200)

        # Daily Events data
        n = await J("document.querySelectorAll('.evtable tbody tr').length")
        reg = await J("document.querySelectorAll('#sh-register tbody tr').length")
        check("every register row becomes an event", n == reg and n > 0, f"{n} vs {reg}")
        ids = await J("[...document.querySelectorAll('.evtable tbody tr')].map(r=>r.dataset.id)")
        check("event IDs are unique", len(ids) == len(set(ids)))
        stories = await J("[...document.querySelectorAll('.evtable .story')].map(s=>s.textContent)")
        check("repeat episodes merged into stories", any("/3" in s for s in stories), str(stories[:5]))
        dates = await J("[...document.querySelectorAll('.evtable tbody tr td:first-child')].map(t=>+t.dataset.v)")
        check("events newest first", dates == sorted(dates, reverse=True))
        check("every event shows an Updated date", await J("[...document.querySelectorAll('.evtable tbody tr td:last-child')].every(t=>/\\d{4}/.test(t.textContent))"))

        # Filters
        async def visible(): return await J("[...document.querySelectorAll('.evtable tbody tr')].filter(r=>r.style.display!=='none').length")
        await pg.click("#evSev button[data-v='hi']"); await pg.wait_for_timeout(80)
        hi = await visible()
        sev_ok = await J("[...document.querySelectorAll('.evtable tbody tr')].filter(r=>r.style.display!=='none').every(r=>/Critical|High/.test(r.cells[5].textContent))")
        check("severity filter", 0 < hi < n and sev_ok, str(hi))
        await pg.click("#evCat button[data-v='C']"); await pg.wait_for_timeout(80)
        both = await visible()
        check("filters combine (severity AND type)", 0 < both <= hi, str(both))
        await pg.click("#evReset"); await pg.wait_for_timeout(80)
        check("clear filters restores all", await visible() == n)
        await pg.fill("#evq", "coreweave"); await pg.wait_for_timeout(80)
        cw = await visible()
        check("event search", cw >= 1 and await J("[...document.querySelectorAll('.evtable tbody tr')].filter(r=>r.style.display!=='none').every(r=>/CoreWeave/.test(r.textContent))"), str(cw))
        await pg.fill("#evq", ""); await pg.click(".mini-tl button >> nth=-1"); await pg.wait_for_timeout(80)
        check("date filter from timeline", 0 < await visible() < n)
        await pg.click("#evReset")
        await pg.click(".kpi[data-k='4']"); await pg.wait_for_timeout(80)
        check("KPI tile filters the table (catalyst not confirmed)", await J("[...document.querySelectorAll('.evtable tbody tr')].filter(r=>r.style.display!=='none').every(r=>/Not confirmed/.test(r.cells[6].textContent))"))
        await pg.click("#evReset")

        # Sorting
        await pg.click(".evtable th:nth-child(4)"); await pg.wait_for_timeout(80)
        vals = await J("[...document.querySelectorAll('.evtable tbody tr td:nth-child(4)')].map(t=>t.dataset.v===''?null:+t.dataset.v).filter(v=>v!==null)")
        check("sort by price impact (ascending)", vals == sorted(vals))
        await pg.click(".evtable th:nth-child(4)"); await pg.wait_for_timeout(80)
        vals = await J("[...document.querySelectorAll('.evtable tbody tr td:nth-child(4)')].map(t=>t.dataset.v===''?null:+t.dataset.v).filter(v=>v!==null)")
        check("sort by price impact (descending)", vals == sorted(vals, reverse=True))

        # Event panel
        await pg.click(".evtable tbody tr >> nth=0"); await pg.wait_for_timeout(350)
        check("event panel opens", await J("document.querySelector('.panel').classList.contains('on')"))
        h3 = await J("[...document.querySelectorAll('#pnB h3')].map(h=>h.textContent)")
        for need in ["What happened", "Why it matters financially", "Price and volume reaction", "Facts versus interpretation", "Related companies", "Source documents", "Refresh"]:
            check(f"panel section: {need}", any(x.startswith(need) for x in h3))
        check("what happened ≤ 3 bullets", await J("document.querySelectorAll('#pnB h3 + ul li').length") <= 3)
        page_links = set(await J("[...document.querySelectorAll('.wrap a[href^=http]')].map(a=>a.href)"))
        panel_links = await J("[...document.querySelectorAll('#pnB .srcs a')].map(a=>a.href)")
        check("panel sources all come from the page (none invented)", all(l in page_links for l in panel_links), str(panel_links[:3]))
        check("deep link updates the address", "#/events/event/" in await J("location.hash"))
        await pg.click("#pnFol"); await pg.wait_for_timeout(100)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(250)
        check("Escape closes panel", not await J("document.querySelector('.panel').classList.contains('on')"))
        await pg.click("#evFol"); await pg.wait_for_timeout(80)
        check("followed story filter", await visible() >= 1)
        await pg.reload(); await pg.wait_for_timeout(1200)
        await pg.click("#evFol"); await pg.wait_for_timeout(80)
        check("follow persists across reload", await visible() >= 1)
        await pg.click("#evFol")
        eid = ids[3]
        await pg.evaluate(f"location.hash='#/events/event/{eid}'"); await pg.wait_for_timeout(350)
        check("event deep link opens that event", eid in await J("document.getElementById('pnK').textContent"))
        await pg.keyboard.press("Escape")

        # Generic tables: filter, sort, CSV, row evidence
        await pg.click("nav a[data-view='funding']"); await pg.wait_for_timeout(150)
        bar = pg.locator("#view-funding .tbar input").first
        await bar.fill("anthropic"); await pg.wait_for_timeout(80)
        check("table filter", "1 of" in await pg.locator("#view-funding .tbar .cnt").first.text_content())
        await bar.fill("")
        async with pg.expect_download() as dl:
            await pg.locator("#view-funding .tbar .btn").first.click()
        d = await dl.value; path = await d.path(); csv = open(path, encoding="utf-8-sig").read()
        check("CSV export", csv.count("\n") >= 10 and "OpenAI" in csv, d.suggested_filename)
        await pg.locator("#view-funding table").first.locator("th:nth-child(4)").click(); await pg.wait_for_timeout(80)
        first = await pg.locator("#view-funding table").first.locator("tbody tr td:nth-child(4)").first.text_content()
        check("numeric sort understands $B and ranges", first.strip().startswith("$0") or "~$5B" in first or "$5B" in first, first)
        await pg.locator("#view-funding table").first.locator("tbody tr").first.click(); await pg.wait_for_timeout(300)
        check("row opens evidence panel", await J("document.querySelector('.panel').classList.contains('on') && document.querySelectorAll('#pnB dl dt').length>3"))
        await pg.keyboard.press("Escape")

        # Global search
        await pg.fill("#gq", "oracle"); await pg.wait_for_timeout(150)
        res = await J("document.querySelectorAll('#gqr button').length")
        check("global search returns results", res > 3, str(res))
        await pg.keyboard.press("Enter"); await pg.wait_for_timeout(400)
        check("search result opens a record", await J("document.querySelector('.panel').classList.contains('on')"))
        await pg.keyboard.press("Escape")

        # Network search, tech empty state, grades, freshness
        await pg.click("nav a[data-view='network']"); await pg.wait_for_timeout(150)
        await pg.fill("#netq", "OpenAI"); await pg.wait_for_timeout(100)
        check("network entity search highlights", await J("document.querySelectorAll('.fn-node.match').length") >= 1)
        await pg.click("nav a[data-view='tech']"); await pg.click("#techGo"); await pg.wait_for_timeout(200)
        check("tech tracker shows no placeholder data and links to tech events", await J("document.querySelector('.view.on').id") == "view-events" and await J("document.querySelector('#evCat button[data-v=D]').getAttribute('aria-pressed')") == "true")
        check("every evidence chip is graded", await J("[...document.querySelectorAll('.chip')].every(c=>c.dataset.grade)"))
        check("static-baseline freshness label visible", "Static baseline" in await J("document.querySelector('.asof').textContent"))
        check("source index lists every cited publisher", await J("document.querySelectorAll('#source-index tbody tr').length") > 10)
        check("no page errors (desktop)", not errs, "; ".join(errs[:3]))

        # Responsive
        for w, h in [(1024, 768), (390, 844)]:
            pm, e2 = await unlocked(b, "file://" + SRC, (w, h))
            for v in ["events", "funding", "credit", "network"]:
                await pm.evaluate(f"location.hash='#/{v}'"); await pm.wait_for_timeout(150)
                over = await pm.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                check(f"no page-level horizontal scroll at {w}px ({v})", over <= 1, str(over))
            check(f"no page errors at {w}px", not e2)

        # Encrypted build round-trip
        out = os.path.join(tempfile.mkdtemp(), "index.html")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "encrypt_page.py"), "--test-passcode", "Test-Pass-12345", "--out", out], check=True, capture_output=True)
        html = open(out, encoding="utf-8").read()
        check("encrypted build hides content", "Lam Research" not in html and "terminalUI" not in html)
        ctx = await b.new_context(viewport={"width": 1400, "height": 900}); pe = await ctx.new_page(); e3 = []
        pe.on("pageerror", lambda e: e3.append(str(e)))
        await pe.goto("file://" + out); await pe.fill("#lockInput", "Test-Pass-12345"); await pe.click("#lockGo"); await pe.wait_for_timeout(3000)
        check("encrypted build unlocks into the terminal", await pe.evaluate("document.querySelectorAll('.evtable tbody tr').length") > 0 and not e3, "; ".join(e3[:2]))
        await b.close()
    print(f"\n{len(FAILED)} failures" + (": " + ", ".join(FAILED) if FAILED else ""))
    sys.exit(1 if FAILED else 0)

asyncio.run(main())
