"""Optional real-browser smoke. Uses isolated storage and a fresh headless browser.

Run: .venv/Scripts/python.exe tests/ui/browser_smoke.py
No production account, existing browser session or remote debugging is used.
"""
import json
from io import BytesIO
from decimal import Decimal
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from zipfile import ZipFile

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "outputs/ui_review"


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="pilog_ui_browser_") as temporary:
        environment = {**os.environ, "PILOG_UI_OUTPUT_ROOT": temporary, "PYTHONDONTWRITEBYTECODE": "1"}
        with (Path(temporary) / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "apps/streamlit_app.py",
                "--server.port", str(port), "--server.address", "127.0.0.1", "--server.fileWatcherType", "none"],
                cwd=ROOT, env=environment, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                url = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 25
                while True:
                    try:
                        with urlopen(url + "/_stcore/health", timeout=2) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        pass
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("UI server did not become ready")
                    time.sleep(0.2)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(channel="msedge", headless=True)
                    context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    def settle():
                        page.wait_for_load_state("networkidle", timeout=15000)
                        page.wait_for_function("""() => {
                            const app = document.querySelector('[data-testid="stApp"]');
                            return app && app.getAttribute('data-test-script-state') === 'notRunning';
                        }""", timeout=20000)
                        page.evaluate("document.fonts.ready")

                    def capture(name, heading, anchor=None):
                        settle()
                        target = anchor if anchor is not None else (page.locator(".workspace-header") if heading == "CFR Decision Workspace" else page.get_by_role("heading", name=heading, exact=True))
                        target.evaluate("e => e.scrollIntoView({block: 'start'})")
                        # Wait for visible canvas tables to paint, independently of Python's rerun state.
                        page.wait_for_function("""() => Array.from(document.querySelectorAll('[data-testid="stDataFrame"]'))
                            .filter(e => {const r=e.getBoundingClientRect(); return e.checkVisibility() && r.width>0 && r.height>0 && r.top>=0 && r.bottom<=innerHeight;})
                            .every(e => Array.from(e.querySelectorAll('canvas')).some(canvas => {
                                const ctx=canvas.getContext('2d'); if(!ctx || !canvas.width || !canvas.height) return false;
                                const pixels=ctx.getImageData(0,0,canvas.width,canvas.height).data;
                                let ink=0; for(let i=0;i<pixels.length;i+=4) {
                                    if(pixels[i+3]>0 && pixels[i]<140 && pixels[i+1]<160 && pixels[i+2]<190 && ++ink>20) return true;
                                } return false;
                            }))""", timeout=15000)
                        page.screenshot(path=str(ARTIFACTS / name))

                    page.goto(url)
                    expect(page.get_by_role("heading", name="CFR Decision Workspace", exact=True)).to_be_visible(timeout=25000)
                    expect(page.get_by_text("Belum dihitung.", exact=True)).to_be_visible()
                    logo = page.locator('section[data-testid="stSidebar"] img')
                    expect(logo).to_have_count(1)
                    expect(logo).to_be_visible()
                    assert logo.evaluate("e => e.complete && e.naturalWidth > 0"), "Official logo did not load"
                    expect(page.get_by_text("PILOG / COMMERCIAL", exact=True)).to_have_count(0)
                    expect(page.get_by_text("Periksa sumber dan basis pengiriman sebelum menghitung.", exact=True)).to_have_count(0)
                    expect(page.get_by_label("Pilih profil kapal", exact=True)).to_be_visible()
                    expect(page.get_by_text("Target hasil harian (USD/hari)", exact=True)).to_be_visible()
                    expect(page.locator('[data-testid="stDataFrame"]').first).to_be_visible()
                    capture("01_initial.png", "CFR Decision Workspace")
                    picker = page.get_by_label("Pilih profil kapal", exact=True)
                    expect(picker).to_have_count(1)
                    assert picker.evaluate("e => e.getBoundingClientRect().top < document.querySelector('#pilog-step-02').getBoundingClientRect().top")
                    picker.click()
                    picker.press("ArrowDown")
                    page.get_by_role("option").filter(has_text="54.000").click()
                    expect(page.get_by_text("Supramax · 54.000,00 DWT · 12,00 knot → acuan Supramax (58 000 dwt)", exact=True)).to_be_visible()
                    picker.click()
                    picker.press("ArrowDown")
                    page.get_by_role("option").filter(has_text="38.000").click()
                    expect(page.get_by_text("Handysize · 38.000,00 DWT · 12,50 knot → acuan Handysize (38 000 dwt)", exact=True)).to_be_visible()
                    picker.click()
                    picker.press("ArrowDown")
                    page.get_by_role("option").filter(has_text="36.000").click()
                    expect(page.get_by_text("Handysize · 36.000,00 DWT · 11,50 knot → acuan Handysize (38 000 dwt)", exact=True)).to_be_visible()
                    settle()
                    expect(page.get_by_text("Handymax memakai acuan pasar Handysize 38k sebagai proxy kelas.", exact=True)).to_have_count(0)
                    voyage_picker = page.get_by_label("Pilih Voyage Estimate", exact=True)
                    expect(voyage_picker).to_have_count(1)
                    voyage_picker.click()
                    voyage_picker.press("ArrowDown")
                    page.get_by_role("option").filter(has_text="Bontang → Davao").click()
                    expect(page.get_by_text("Bontang → Davao", exact=True)).to_be_visible()
                    expect(page.get_by_text("28.000,00", exact=True)).to_be_visible()
                    capture("01_davao.png", "Data Pengiriman & Kapal")
                    voyage_picker.click()
                    voyage_picker.press("ArrowDown")
                    page.get_by_role("option").filter(has_text="Bontang → Mundra").click()
                    expect(page.get_by_text("Bontang → Mundra", exact=True)).to_be_visible()
                    page.get_by_role("tab", name="Harga bunker", exact=True).click()
                    expect(page.get_by_text("Singapore 380 CST → fuel oil · Singapore MGO → diesel oil.", exact=True)).to_be_visible()
                    capture("01_bunker.png", "Data Pengiriman & Kapal")
                    page.get_by_role("tab", name="Target harian", exact=True).click()
                    page.get_by_text("Pilihan kapal dan dasar perbandingan", exact=True).click()
                    page.get_by_role("button", name="Bandingkan profil", exact=True).click()
                    expect(page.get_by_text("Freight pembanding sama untuk seluruh profil. Pilihan kapal tetap manual.", exact=True)).to_be_visible(timeout=20000)
                    capture("02_comparison.png", "Voyage Economics")
                    page.get_by_text("Pilihan kapal dan dasar perbandingan", exact=True).click()
                    page.get_by_role("button", name="Hitung ekonomi voyage", exact=True).click()
                    expect(page.get_by_text("Durasi voyage (hari)", exact=True)).to_be_visible()
                    capture("02_voyage.png", "Voyage Economics")
                    page.get_by_role("button", name="Tetapkan freight untuk tender", exact=True).click()
                    page.get_by_text("Edit bid & risiko", exact=True).click()
                    page.get_by_role("button", name="Isi contoh bid tiga putaran", exact=True).click()
                    expect(page.get_by_role("button", name="Isi contoh bid tiga putaran", exact=True)).to_have_count(0, timeout=20000)
                    page.get_by_role("button", name="Terapkan bid & risiko", exact=True).click()
                    expect(page.get_by_role("button", name="Terapkan bid & risiko", exact=True)).to_have_count(0, timeout=20000)
                    for number in (1, 2, 3):
                        expect(page.get_by_role("heading", name=f"Putaran {number}", exact=True)).to_have_count(1)
                        # Canvas headers/values are verified in AppTest; browser verifies each distinct round card.
                        expect(page.locator(f'.st-key-tender_round_{number} [data-testid="stDataFrame"]')).to_have_count(1)
                    capture("02_tender.png", "Tendering")
                    # Random inputs are not required to yield GO. Use the explicit
                    # scripted GO fixture for the existing GO/download checks.
                    page.get_by_role("button", name="Muat contoh GO", exact=True).click()
                    expect(page.get_by_text("Bid dan skenario risiko: contoh acak.", exact=True)).to_have_count(0, timeout=20000)
                    page.get_by_role("button", name="Evaluasi tender & DSS", exact=True).click()
                    expect(page.locator(".decision-banner .action")).to_have_text("GO", timeout=20000)
                    capture("03_go.png", "Commercial Decision Brief")
                    expect(page.get_by_text("Estimasi pendapatan, biaya dan hasil neto", exact=True)).to_be_visible()
                    expect(page.get_by_text("Hasil mengacu pada input terakhir yang diterapkan. Estimasi kontribusi satu pengiriman, bukan laba bersih perusahaan atau award tender.", exact=True)).to_have_count(0)
                    page.get_by_text("Analisis pendukung", exact=True).click()
                    page.get_by_role("tab", name="Risiko", exact=True).click()
                    capture("03_risk.png", "Commercial Decision Brief", page.get_by_text("Sensitivitas biaya", exact=True))
                    page.get_by_role("tab", name="Dampak logistik", exact=True).click()
                    expect(page.get_by_text("Cakupan lanjutan: DWCC, kesiapan kapal/terminal dan jadwal/laycan.", exact=True)).to_be_visible()
                    page.get_by_role("tab", name="Konsekuensi harga", exact=True).click()
                    expect(page.get_by_text("FOB = indeks + alpha buyer · CFR = FOB + freight tetap", exact=True)).to_be_visible()
                    page.get_by_text("Analisis pendukung", exact=True).click()
                    with page.expect_download() as download_info:
                        page.get_by_role("button", name="Unduh decision brief", exact=True).click()
                    download = download_info.value
                    download.save_as(str(ARTIFACTS / "downloaded_brief.md"))
                    assert "# GO" in (ARTIFACTS / "downloaded_brief.md").read_text(encoding="utf-8")
                    with page.expect_download() as json_download:
                        page.get_by_role("button", name="Unduh hasil JSON", exact=True).click()
                    json_path = Path(json_download.value.path())
                    downloaded_result = json.loads(json_path.read_text(encoding="utf-8"))
                    assert downloaded_result["pricing"]["commission_fraction"] == "0"
                    assert Decimal(downloaded_result["baseline"]["commission_usd"]) == 0
                    assert "od_comparison" not in downloaded_result
                    assert downloaded_result["route_distance"]["cell"] == "H11"
                    with page.expect_download() as zip_download:
                        page.get_by_role("button", name="Unduh paket + snapshot", exact=True).click()
                    with ZipFile(BytesIO(Path(zip_download.value.path()).read_bytes())) as package:
                        packaged = json.loads(package.read("result.json"))
                        assert packaged["run_id"] == downloaded_result["run_id"]
                        assert packaged["commercial_financials"] == downloaded_result["commercial_financials"]
                        assert "input_snapshot/case_fixture.json" in package.namelist()
                        assert "input_snapshot/od_distance.json" in package.namelist()
                    page.get_by_text("Edit bid & risiko", exact=True).click()
                    expect(page.get_by_role("button", name="Evaluasi tender & DSS", exact=True)).to_be_disabled()
                    expect(page.get_by_role("button", name="Unduh decision brief", exact=True)).to_have_count(0)
                    page.get_by_text("Edit bid & risiko", exact=True).click()
                    page.get_by_text("Perbarui estimasi biaya", exact=True).click()
                    expect(page.get_by_role("button", name="Evaluasi tender & DSS", exact=True)).to_be_disabled()
                    expect(page.get_by_role("button", name="Unduh decision brief", exact=True)).to_have_count(0)
                    page.get_by_label("Total pelabuhan dan biaya lain (USD) — estimasi terbaru", exact=True).fill("600000")
                    page.get_by_label("Alasan perubahan biaya", exact=True).fill("Synthetic browser test updated port costs")
                    page.get_by_role("button", name="Terapkan estimasi biaya", exact=True).click()
                    expect(page.get_by_role("button", name="Terapkan estimasi biaya", exact=True)).to_have_count(0, timeout=20000)
                    page.get_by_role("button", name="Evaluasi tender & DSS", exact=True).click()
                    expect(page.locator(".decision-banner .action")).to_have_text("NO GO", timeout=20000)
                    expect(page.get_by_text("Gate A: Lolos; Gate B: Tidak lolos.", exact=True)).to_be_visible()
                    capture("04_no_go_economics.png", "Commercial Decision Brief")
                    with page.expect_download() as economic_download:
                        page.get_by_role("button", name="Unduh hasil JSON", exact=True).click()
                    economic = json.loads(Path(economic_download.value.path()).read_text(encoding="utf-8"))
                    assert economic["input_lineage"]["context"]["freight_tender"] == downloaded_result["input_lineage"]["context"]["freight_tender"]
                    assert economic["tender"] == downloaded_result["tender"]
                    assert Decimal(economic["baseline"]["contribution_usd"]) < 0
                    page.get_by_role("button", name="Muat contoh NO GO", exact=True).click()
                    expect(page.get_by_text("Estimasi biaya terbaru:", exact=False)).to_have_count(0, timeout=20000)
                    expect(page.get_by_role("button", name="Unduh decision brief", exact=True)).to_have_count(0, timeout=20000)
                    page.get_by_role("button", name="Evaluasi tender & DSS", exact=True).click()
                    expect(page.locator(".decision-banner .action")).to_have_text("NO GO", timeout=20000)
                    expect(page.get_by_text("Gate B belum dievaluasi.", exact=True)).to_be_visible()
                    capture("04_no_go.png", "Commercial Decision Brief")
                    with page.expect_download() as before_random_download:
                        page.get_by_role("button", name="Unduh hasil JSON", exact=True).click()
                    before_random=json.loads(Path(before_random_download.value.path()).read_text(encoding="utf-8"))
                    page.get_by_text("Edit bid & risiko", exact=True).click()
                    page.get_by_role("button", name="Acak ulang bid & risiko", exact=True).click()
                    settle()
                    expect(page.get_by_text("Contoh acak belum diterapkan.", exact=True)).to_be_visible()
                    expect(page.get_by_role("button", name="Unduh hasil JSON", exact=True)).to_have_count(0)
                    page.get_by_role("button", name="Acak ulang bid & risiko", exact=True).click()
                    settle()
                    capture("04_random_editor.png", "Tendering")
                    page.get_by_role("button", name="Terapkan bid & risiko", exact=True).click()
                    expect(page.get_by_text("Bid dan skenario risiko: contoh acak.", exact=True)).to_be_visible()
                    page.get_by_role("button", name="Evaluasi tender & DSS", exact=True).click()
                    expect(page.get_by_role("button", name="Unduh hasil JSON", exact=True)).to_be_visible()
                    with page.expect_download() as random_download:
                        page.get_by_role("button", name="Unduh hasil JSON", exact=True).click()
                    random_report=json.loads(Path(random_download.value.path()).read_text(encoding="utf-8"))
                    random_context=random_report["input_lineage"]["context"]
                    assert random_context["freight_tender"]==before_random["input_lineage"]["context"]["freight_tender"]
                    assert len(random_context["bids"])==9 and len(random_context["scenarios"])==3
                    assert random_context["tender_example"]["source_status"]=="simulation_only_randomized_example"
                    assert not random_context["tender_example"]["edited_before_apply"]
                    assert "DATA_ISSUE" not in random_report["recommendation"]["reason_codes"]
                    capture("04_random_result.png", "Commercial Decision Brief")
                    page.get_by_role("button", name="Kasus baru", exact=True).click()
                    page.get_by_text("Ubah input kasus", exact=True).click()
                    page.get_by_label("Kecepatan muat (MT/hari)", exact=True).fill("0")
                    page.get_by_role("button", name="Terapkan input", exact=True).click()
                    page.get_by_role("button", name="Hitung ekonomi voyage", exact=True).click()
                    expect(page.get_by_text("Voyage belum dapat dihitung: NONPOSITIVE_INPUT:loading_rate_mt_day", exact=True)).to_be_visible()
                    page.get_by_role("button", name="Muat contoh GO", exact=True).click()
                    page.set_viewport_size({"width": 390, "height": 844})
                    capture("05_narrow.png", "CFR Decision Workspace")
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Page overflows viewport"
                    assert not errors, errors
                    result_files = list((Path(temporary) / "runs").glob("*/result.json"))
                    reports = [json.loads(p.read_text(encoding="utf-8")) for p in result_files]
                    actions = [r["recommendation"]["action"] for r in reports]
                    scripted = [r["recommendation"]["action"] for r in reports if not r["input_lineage"]["context"].get("tender_example")]
                    assert sorted(scripted) == ["GO", "NO_GO", "NO_GO"], scripted
                    assert len(reports)==4 and random_report["recommendation"]["action"] in {"GO","NO_GO"}, actions
                    browser.close()
                    print(json.dumps({"browser_smoke": "PASS", "actions": actions, "javascript_errors": errors,
                                  "screenshots": str(ARTIFACTS), "test_storage": "isolated temporary directory"}))
            finally:
                if os.name == "nt" and process.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)


if __name__ == "__main__":
    main()
