"""New widget E2E replaces only the v1 navigation-specific test."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from services.workspace import Workspace
from ui.navigation import ROUTES

def click(at,label):
    next(b for b in at.button if b.label==label).click().run(timeout=120)
    assert not at.exception, [x.message for x in at.exception]
    assert not at.error, [x.value for x in at.error]
    return at

def navigate(at,page): return click(at,page)

def test_end_to_end_widgets(tmp_path,monkeypatch):
    monkeypatch.setenv('ESS_DATA_DIR',str(tmp_path/'ui_workspace'))
    at=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=120).run()
    assert not at.exception and not at.error
    for group,pages in ROUTES.items():
        for page in pages:navigate(at,page)
    navigate(at,'Screening');click(at,'Execute screening')
    navigate(at,'Component Explorer');click(at,'Save review note');click(at,'Generate component report')
    navigate(at,'Predictive Analytics');click(at,'Predict active batch')
    navigate(at,'Model Evaluation');click(at,'Evaluate screening policy')
    navigate(at,'Reports & Exports');click(at,'Generate report files')
    navigate(at,'Model Laboratory');click(at,'Train candidate models')
    next(x for x in at.checkbox if x.label.startswith('Confirm this model')).check().run()
    click(at,'Activate selected model')
    navigate(at,'Policy Center');click(at,'Validate and preview policy');click(at,'Simulate policy on active batch')
    next(x for x in at.checkbox if x.label.startswith('I confirm')).check().run();click(at,'Save policy version')
    navigate(at,'Scenario Simulator');next(x for x in at.selectbox if x.label=='Scenario').set_value('Early Warning').run();click(at,'Run scenario')
    navigate(at,'System Diagnostics');click(at,'Run minimal backend smoke test')
    navigate(at,'Settings');click(at,'Save workspace settings');click(at,'Create workspace backup')
    next(x for x in at.checkbox if x.label.startswith('Confirm creation')).check().run();click(at,'Reset demo workspace')
    next(x for x in at.selectbox if x.label=='Active batch').set_value('').run()
    navigate(at,'Overview');assert any('Select a batch' in x.value for x in at.info)
