import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from backend.modules.fines.lookup import FineLookup
from backend.modules.rules.loader import RulesLoader
from backend.modules.agent.engine import AgentEngine

class MockGeofencing:
    def get_rules_for_location(self, loc):
        return []

if __name__ == "__main__":
    engine = AgentEngine(
        fine_lookup=FineLookup('backend/data/fines.db'),
        rules_loader=RulesLoader('backend/data/rules.json'),
        geofencing_engine=MockGeofencing()
    )
    res = engine.run('fine for overspeeding in delhi')
    print('\nBOT RESPONSE:\n', res['response'])
