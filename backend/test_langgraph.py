import os
import sys
import json
os.environ['GROQ_API_KEY'] = 'dummy'

# Mock tools executor to avoid needing the DBs for this test
class MockToolExecutor:
    def execute(self, name, kwargs, gps):
        return {"mock": "result"}

try:
    from modules.agent.engine import AgentEngine
    from backend.modules.agent.tools import TOOL_DEFINITIONS
    
    agent = AgentEngine(None, None, None)
    agent.tool_executor = MockToolExecutor()
    
    # Force _run_groq
    agent.groq_available = True
    agent.ollama_available = False
    agent.gemini_available = False
    
    res = agent._run_groq("I got caught riding a bike with three people on it in Tamil Nadu.", [], None)
    print(json.dumps(res, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
