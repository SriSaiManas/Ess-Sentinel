import pytest
from ess.data.synthetic import generate
from ess.prediction.training import train
@pytest.fixture(scope='session')
def dataset(): return generate(800,12)
@pytest.fixture(scope='session')
def bundle(dataset): return train(dataset)
