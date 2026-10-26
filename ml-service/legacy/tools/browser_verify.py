"""Optional real-browser E2E: pip install playwright; playwright install chromium.
Set ESS_BROWSER_EXECUTABLE only to use an already installed Chromium executable.
Runs a temporary isolated workspace and never alters user's saved batches.
"""
import os,sys,subprocess,tempfile,time,json,urllib.request,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence'/'screenshots';OUT.mkdir(parents=True,exist_ok=True)
app_python=os.environ.get('ESS_APP_PYTHON',sys.executable)

def main():
    with tempfile.TemporaryDirectory(prefix='ess-browser-') as temp:
        env=os.environ.copy();env['ESS_DATA_DIR']=temp
        log=(ROOT/'evidence/browser_server.log').open('w',encoding='utf-8')
        process=subprocess.Popen([app_python,'-m','streamlit','run','app.py','--server.port=8523'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    urllib.request.urlopen('http://127.0.0.1:8523/_stcore/health',timeout=1);break
                except OSError:time.sleep(.2)
            with sync_playwright() as p:
                custom=os.environ.get('ESS_BROWSER_EXECUTABLE')
                args=['--no-sandbox','--disable-dev-shm-usage']
                if custom:args+=['--use-gl=angle','--use-angle=swiftshader','--single-process']
                browser=p.chromium.launch(headless=True,executable_path=custom or None,args=args)
                page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:8523',wait_until='domcontentloaded')
                expect(page.get_by_role('heading',name='Engineering Intelligence Overview')).to_be_visible(timeout=60000)
                def ready():
                    expect(page.get_by_text('Decision support only. Final component disposition requires qualified engineering review.',exact=True)).to_be_visible(timeout=120000)
                    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
                    expect(page.locator('[data-testid="stAlertContainer"]').filter(has_text='could not complete')).to_have_count(0)
                def nav(label,heading=None):
                    page.get_by_role('button',name=re.compile(r'(?:^|\s)'+re.escape(label)+r'$')).click()
                    expect(page.get_by_role('heading',name=heading or label,exact=True)).to_be_visible(timeout=60000);ready()
                def shot(name):
                    if name in ['01_overview.png','03_anomaly.png','05_component.png']:
                        page.locator('.js-plotly-plot').first.wait_for(state='visible',timeout=60000)
                    page.screenshot(path=str(OUT/name),full_page=True)
                ready();shot('01_overview.png')
                nav('Screening','Screening Workbench');page.get_by_role('button',name=re.compile('Execute screening$')).click();ready();shot('02_screening.png')
                nav('Anomaly Analysis');shot('03_anomaly.png')
                nav('Model Laboratory');shot('04_model_laboratory.png')
                nav('Component Explorer');shot('05_component.png')
                page.get_by_role('tab',name='Review & history',exact=True).click()
                page.get_by_role('textbox',name='Engineering review note',exact=True).fill('Browser-verified review annotation.')
                page.get_by_role('button',name='Save review note',exact=True).click();ready()
                nav('Reports & Exports');page.get_by_role('button',name=re.compile('Generate report files$')).click()
                expect(page.get_by_role('button',name='Download PDF',exact=True)).to_be_visible(timeout=60000)
                with page.expect_download() as download:
                    page.get_by_role('button',name='Download PDF',exact=True).click()
                file=Path(download.value.path());assert file.read_bytes().startswith(b'%PDF')
                shot('06_reports.png')
                nav('Data Ingestion')
                page.locator('input[type=file]').set_input_files(str(ROOT/'data/example_synthetic.csv'))
                expect(page.get_by_role('heading',name='Normalized preview',exact=True)).to_be_visible(timeout=60000)
                page.get_by_role('textbox',name='Batch name',exact=True).fill('Browser imported batch')
                page.get_by_role('textbox',name='Batch name',exact=True).press('Tab')
                page.get_by_text('I reviewed mappings and units and confirm importing this dataset.',exact=True).click()
                expect(page.get_by_role('checkbox',name='I reviewed mappings and units and confirm importing this dataset.',exact=True)).to_be_checked()
                expect(page.get_by_role('button',name='Commit dataset',exact=True)).to_be_enabled(timeout=60000)
                page.get_by_role('button',name='Commit dataset',exact=True).click()
                expect(page.locator('.ess-batch b')).to_have_text('Browser imported batch',timeout=60000)
                ready()
                nav('Batch Explorer');expect(page.locator('.ess-batch b')).to_have_text('Browser imported batch',timeout=30000)
                nav('Overview','Engineering Intelligence Overview')
                expect(page.get_by_text('The batch is ready for screening. No results have been invented.',exact=True)).to_be_visible(timeout=60000)
                page.set_viewport_size({'width':900,'height':900})
                page.get_by_role('heading',name='Engineering Intelligence Overview',exact=True).scroll_into_view_if_needed()
                shot('07_laptop_overview.png')
                assert page.locator('body').evaluate('(el)=>el.scrollWidth <= window.innerWidth+5')
                page.set_viewport_size({'width':1920,'height':1080})
                nav('System Diagnostics');page.get_by_role('button',name='Run minimal backend smoke test',exact=True).click();ready()
                browser.close()
                (ROOT/'evidence/browser_results.json').write_text(json.dumps({'status':'passed','application_python':app_python,'browser':'Chromium','screenshots':sorted(x.name for x in OUT.glob('*.png')),'verified':['launch','six page screenshots','screening execution','component review save','PDF byte download','CSV upload / mapping preview / commit','batch context','900px viewport no body overflow','diagnostics smoke'],'page_errors':errors},indent=2))
                assert not errors,errors
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close()
if __name__=='__main__':main()
