"""Rebuild trusted demonstration model for the installed sklearn version."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'ml-service'/'legacy';sys.path.insert(0,str(root))
from ess.data.validation import ingest
from ess.prediction.training import train,save_bundle
import sklearn,pandas,numpy
bundle=train(ingest((root/'data/example_synthetic.csv').read_bytes(),'demo.csv'))
bundle['manifest']['runtime']={'scikit-learn':sklearn.__version__,'pandas':pandas.__version__,'numpy':numpy.__version__}
save_bundle(bundle,root/'models/demo')
print('Rebuilt demo model with installed dependencies:',bundle['manifest']['runtime'])
