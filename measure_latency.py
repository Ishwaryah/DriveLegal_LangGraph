import time
import os
import sys

_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.modules.nlp.pipeline import NLPPipeline
from backend.modules.response.builder import ResponseBuilder

# Minimal init
nlp = NLPPipeline()
builder = ResponseBuilder(fine_lookup=None, rules_loader=None, geofencing_engine=None)

t0 = time.time()
res = nlp.run("fine for no helmet in chennai")
print(f"NLP Pipeline Latency: {(time.time() - t0) * 1000:.2f} ms")
print(res)
