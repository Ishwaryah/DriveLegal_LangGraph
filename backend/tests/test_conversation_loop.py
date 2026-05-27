import pytest
import sys
import os
import json
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
        self.chat = self.MockChat()
        self.call_history = []

    class MockChat:
        def __init__(self):
            self.completions = self.MockCompletions()

        class MockCompletions:
            def create(self, model, messages, tools=None, tool_choice=None, max_tokens=None, temperature=None):
                last_message = messages[-1]["content"].lower()
                
                class Choice:
                    def __init__(self, message):
                        self.message = message
                        
                class Message:
                    def __init__(self, content, tool_calls=None):
                        self.content = content
                        self.tool_calls = tool_calls
                        
                class ToolCall:
                    def __init__(self, name, arguments):
                        self.id = "call_123"
                        self.function = self.Function(name, arguments)
                        
                    class Function:
                        def __init__(self, name, arguments):
                            self.name = name
                            self.arguments = json.dumps(arguments)

                if "amount_inr" in last_message or "1000" in last_message:
                    return type("Response", (), {"choices": [Choice(Message("The fine is ₹1000 in Delhi.", None))]})
                    
                if "speeding" in last_message:
                    is_delhi = False
                    for m in messages:
                        if m["role"] == "user" and "delhi" in m["content"].lower():
                            is_delhi = True
                            break
                    if is_delhi:
                        return type("Response", (), {"choices": [Choice(Message(None, [ToolCall("lookup_fine", {"offence_type": "SPEED_EXCESS", "state": "Delhi"})]))]})
                    else:
                        return type("Response", (), {"choices": [Choice(Message("Which state?", None))]})
                
                return type("Response", (), {"choices": [Choice(Message("Hello, how can I help you?", None))]})

def test_conversation_history_loop():
    engine = AgentEngine(None, None, None)
    engine.groq_available = True
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
