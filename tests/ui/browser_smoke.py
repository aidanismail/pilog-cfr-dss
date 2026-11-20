"""Isolated local browser check. Never connects to Fleetra or user's browser."""
import json, os, socket, subprocess, sys, time
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from urllib.request import urlopen
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
ARTIFACTS=ROOT/"outputs/ui_review"

@contextmanager
def scratch_dir():
    parent = ARTIFACTS.resolve()
    folder = parent / ("pilog_freight_browser_" + uuid4().hex)
    folder.mkdir()
    try:
        yield folder
    finally:
        resolved = folder.resolve()
        if resolved.parent == parent and not folder.is_symlink():
            rmtree(resolved)


def main():
    ARTIFACTS.mkdir(parents=True,exist_ok=True)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1",0));port=reservation.getsockname()[1]
    with scratch_dir() as folder:
        temporary=str(folder)
        env=dict(os.environ,PILOG_UI_OUTPUT_ROOT=temporary,PYTHONDONTWRITEBYTECODE="1",TEMP=temporary,TMP=temporary)
        with (folder/"server.log").open("w",encoding="utf-8") as log:
            engine = Path(sys.executable)
            process=subprocess.Popen([str(engine),"-m","streamlit","run","apps/streamlit_app.py",
                "--server.port",str(port),"--server.address","127.0.0.1","--server.fileWatcherType","none"],
                cwd=ROOT,env=env,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
            errors=[];downloads=[]
            try:
                url=f"http://127.0.0.1:{port}"
                deadline=time.monotonic()+30
                while True:
                    try:
                        if urlopen(url+"/_stcore/health",timeout=2).status==200:break
                    except OSError:pass
                    if process.poll() is not None or time.monotonic()>deadline:raise RuntimeError("server not ready")
                    time.sleep(.2)
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(channel="msedge",headless=True)
                    page=browser.new_page(viewport={"width":1440,"height":1000},device_scale_factor=1)
                    page.on("pageerror",lambda error:errors.append(str(error)))
                    def settle():
                        page.wait_for_function("""() => {
                            const app=document.querySelector('[data-testid="stApp"]');
                            return app && app.getAttribute('data-test-script-state')==='notRunning';
                        }""",timeout=30000)
                        page.evaluate("document.fonts.ready")
                        page.wait_for_timeout(350)
                    page.goto(url)
                    expect(page.get_by_role("button",name="Hitung freight",exact=True)).to_be_visible(timeout=120000)
                    settle()
                    def current_case(filename):
                        with page.expect_download() as dl:
                            page.get_by_role("button", name="Download kasus", exact=True).click()
                        path = folder / filename
                        dl.value.save_as(str(path))
                        return json.loads(path.read_bytes())["case"]

                    before_reload = current_case("before_reload.json")
                    page.reload()
                    expect(page.get_by_role("button", name="Hitung freight", exact=True)).to_be_visible(timeout=120000)
                    settle()
                    after_reload = current_case("after_reload.json")
                    assert after_reload["kobc_snapshot"]["fetched_at"] > before_reload["kobc_snapshot"]["fetched_at"]
                    assert (after_reload["profile_source"]["live_verification"]["checked_at"] >
                            before_reload["profile_source"]["live_verification"]["checked_at"])
                    if not page.get_by_text("Fearnpulse tidak terhubung", exact=False).count():
                        assert after_reload["market_snapshot"]["fetched_at"] > before_reload["market_snapshot"]["fetched_at"]
                    page.screenshot(path=str(ARTIFACTS/"fd_inputs.png"))
                    page.get_by_role("button",name="Hitung freight",exact=True).click()
                    expect(page.get_by_role("heading",name="Commercial Brief — PILOG",exact=True)).to_be_visible(timeout=30000)
                    settle()
                    page.get_by_role("heading",name="Hasil freight",exact=True).evaluate("e=>e.scrollIntoView({block:'start'})")
                    page.screenshot(path=str(ARTIFACTS/"fd_results.png"))
                    expect(page.get_by_text("Minimum penawaran USD/MT",exact=True).first).to_be_visible()
                    with page.expect_download() as dl:page.get_by_role("button",name="Download brief",exact=True).click()
                    download=dl.value;destination=ARTIFACTS/"fd_commercial_brief.md";download.save_as(str(destination));downloads.append(download.suggested_filename)
                    text=destination.read_text(encoding="utf-8")
                    assert text.count("\n## ")==5 and "SHA-256" in text
                    with page.expect_download() as dl:page.get_by_role("button",name="Download kasus",exact=True).click()
                    case_file=folder/"case.json";dl.value.save_as(str(case_file))
                    payload=json.loads(case_file.read_bytes())
                    payload["case"]["selling_freight_usd_mt"]="1"
                    payload["case"]["sources"]["selling_freight_usd_mt"]["status"]="manual_override"
                    payload["sha256"]=sha256(json.dumps(payload["case"],sort_keys=True,ensure_ascii=False,
                        allow_nan=False,separators=(",",":")).encode("utf-8")).hexdigest()
                    deficit=folder/"deficit.json";deficit.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
                    page.locator('input[type="file"]').set_input_files(str(deficit))
                    expect(page.get_by_text("deficit.json",exact=True)).to_be_visible()
                    page.get_by_role("button",name="Buka kasus",exact=True).click()
                    expect(page.get_by_role("heading",name="Hasil freight",exact=True)).to_have_count(0,timeout=30000)
                    expect(page.get_by_role("button",name="Hitung freight",exact=True)).to_be_visible(timeout=30000)
                    page.get_by_role("button",name="Hitung freight",exact=True).click()
                    expect(page.get_by_text("Naikkan tarif jual atau ubah biaya/operasi sebelum menawarkan.",exact=True).first).to_be_visible(timeout=30000)
                    expect(page.get_by_text("TCE hasil USD/hari",exact=True).first).to_be_visible()
                    settle()
                    page.get_by_role("heading",name="Hasil freight",exact=True).evaluate("e=>e.scrollIntoView({block:'start'})")
                    page.screenshot(path=str(ARTIFACTS/"fd_deficit.png"))
                    page.locator("summary").filter(has_text="Spread matrix").click()
                    expect(page.get_by_text("Kasus dasar.",exact=True)).to_be_visible(timeout=30000)
                    page.get_by_text("Kasus dasar.",exact=True).scroll_into_view_if_needed()
                    page.screenshot(path=str(ARTIFACTS/"fd_matrix.png"))
                    page.set_viewport_size({"width":390,"height":844})
                    close=page.get_by_test_id("stSidebarCollapseButton").locator("button")
                    if close.is_visible():close.evaluate("e=>e.click()")
                    page.get_by_role("heading",name="Automated Freight Desk PILOG",exact=True).evaluate("e=>e.scrollIntoView({block:'start'})")
                    settle()
                    page.screenshot(path=str(ARTIFACTS/"fd_mobile.png"))
                    page.set_viewport_size({"width":1440,"height":1000})
                    if not page.get_by_role("button", name="Buka kasus", exact=True).is_visible():
                        page.get_by_test_id("stExpandSidebarButton").click()
                    risk_case = ROOT / "outputs/test_cases/fd3_risk_pilog_open_hire.json"
                    page.locator('input[type="file"]').set_input_files(str(risk_case))
                    expect(page.get_by_role("button", name="Remove " + risk_case.name, exact=True)).to_be_visible()
                    page.get_by_role("button",name="Buka kasus",exact=True).click()
                    expect(page.get_by_text("Rujukan atau catatan konfirmasi",exact=True).first).to_be_visible(timeout=30000)
                    page.get_by_role("button",name="Hitung freight",exact=True).click()
                    expect(page.get_by_text("Tahan penguncian biaya kapal",exact=False).first).to_be_visible(timeout=30000)
                    with page.expect_download() as dl:
                        page.get_by_role("button",name="Download brief",exact=True).click()
                    path = folder / "risk.md"
                    dl.value.save_as(str(path))
                    brief = path.read_text(encoding="utf-8")
                    assert brief.count("\n## ") == 5 and "45.031,88" in brief and "-2.747,19" in brief and "Kajian beli FFA" in brief
                    assert not errors,errors
                    browser.close()
                report={"status":"PASS","javascript_errors":errors,"downloads":downloads,
                    "checked":["inputs","browser reload refetch","class results","5-section brief download","case package download/import",
                               "deficit quote and TCE","base matrix","390px screenshot","risk case replay and brief"],
                    "agent_server_stopped":True}
                (ARTIFACTS/"fd_browser_result.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
                print(json.dumps(report))
            except Exception:
                print((folder/"server.log").read_text(encoding="utf-8")[-5000:])
                raise
            finally:
                if os.name=="nt":
                    subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True)
                else:
                    process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

if __name__=="__main__":main()
