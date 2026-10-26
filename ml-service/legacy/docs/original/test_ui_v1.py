"""Streamlit script/widget end-to-end harness; ingestion bytes tested in integration."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
PAGES=['Overview','Dataset Validation','Exploratory Analysis','Burn-In Trajectory','Anomaly Detection','Component Detail','Drift Prediction','Model Evaluation','Model Explainability','Reports & Audit','Engineering Policy','Data Import']
def button(at,label): return next(b for b in at.button if b.label==label)
def test_end_to_end_widgets():
    at=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=120).run(); assert not at.exception
    at.radio[0].set_value('Synthetic Generator').run(); button(at,'Generate dataset').click().run(); assert not at.exception
    at.radio[0].set_value('Drift Prediction').run(); button(at,'Train and evaluate models').click().run(timeout=120); assert not at.exception
    button(at,'Screen current batch').click().run(); assert not at.exception
    for page in PAGES:
        at.radio[0].set_value(page).run(); assert not at.exception, (page,[x.message for x in at.exception])
        if page=='Component Detail': button(at,'Generate component report').click().run(); assert not at.exception
        if page=='Reports & Audit': button(at,'Generate batch PDF').click().run(); assert not at.exception
    at.radio[0].set_value('Demo Mode').run()
    next(x for x in at.selectbox if x.label=='Scenario').set_value('Early Warning').run()
    button(at,'Run scenario').click().run(timeout=120); assert not at.exception
    assert at.session_state.results.iloc[0].dynamic_flag
