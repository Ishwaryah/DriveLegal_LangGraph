import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.modules.agent.engine import AgentEngine
from backend.modules.agent.tools import ToolExecutor
class DummyPart:
    def __init__(self, text=None, function_call=None):
        self.text = text
        self.function_call = function_call

    @classmethod
    def from_text(cls, text):
        return cls(text=text)

    @classmethod
    def from_function_call(cls, name, args):
        class FuncCall:
            def __init__(self, n, a):
                self.name = n
                self.args = a
        return cls(function_call=FuncCall(name, args))
        
    @classmethod
    def from_function_response(cls, name, response):
        return cls(text=str(response))

class DummyContent:
    def __init__(self, role=None, parts=None):
        self.role = role
        self.parts = parts

class DummyCandidate:
    def __init__(self, content):
        self.content = content

class DummyTypes:
    Part = DummyPart
    Content = DummyContent
    Candidate = DummyCandidate
    
    class FunctionDeclaration:
        def __init__(self, **kwargs): pass
    
    class Tool:
        def __init__(self, **kwargs): pass
        
    class GenerateContentConfig:
        def __init__(self, **kwargs): pass

types = DummyTypes()

class MockResponse:
    def __init__(self, text, tool_calls=None):
        parts = []
        if text:
            parts.append(types.Part.from_text(text=text))
        if tool_calls:
            for tc in tool_calls:
                parts.append(types.Part.from_function_call(name=tc["name"], args=tc["args"]))
                
        self.candidates = [
            types.Candidate(content=types.Content(parts=parts))
        ]

class MockClient:
    def __init__(self):
        self.models = self.MockModels()
        self.call_history = []

    class MockModels:
        def __init__(self):
            self.parent = None
            
        def generate_content(self, model, contents, config):
            last_message = contents[-1].parts[0].text or ""
            last_message = str(last_message).lower()
            
            if "amount_inr" in last_message:
                return MockResponse(text="The fine is ₹1000 in Delhi.")
                
            if "speeding" in last_message:
                is_delhi = False
                for c in contents:
                    if c.role == "user" and c.parts[0].text and "delhi" in str(c.parts[0].text).lower():
                        is_delhi = True
                        break
                if is_delhi:
                    return MockResponse(
                        text="",
                        tool_calls=[{"name": "lookup_fine", "args": {"offence_type": "SPEED_EXCESS", "state": "Delhi"}}]
                    )
                else:
                    return MockResponse(text="Which state?", tool_calls=None)
            
            return MockResponse(text="Hello, how can I help you?")

def test_conversation_history_loop():
    engine = AgentEngine(None, None, None)
    engine.gemini_available = True
    engine.types = types
    
    mock_client = MockClient()
    mock_client.models.parent = mock_client
    engine.client = mock_client
    
    # Fake tool executor that just returns empty
    engine.tool_executor = ToolExecutor(None, None, None)
    engine.tool_executor.execute = lambda name, params, gps: {"found": True, "amount_inr": 1000}
    
    history = [
        {"role": "user", "parts": ["I live in Delhi."]},
        {"role": "model", "parts": ["Great, how can I help you with traffic laws in Delhi?"]}
    ]
    
    res = engine.run("What is the fine for speeding?", conversation_history=history)
    
    assert res["status"] == "ok"
    assert "Delhi" in res["response"]
    assert "tools_used" in res
    assert len(res["tools_used"]) > 0
    assert res["tools_used"][0]["params"]["state"] == "Delhi"
