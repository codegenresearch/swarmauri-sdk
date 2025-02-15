import pytest
import os
from swarmauri.llms.concrete.GroqToolModel import GroqToolModel
from swarmauri.conversations.concrete.Conversation import Conversation
from swarmauri.tools.concrete.AdditionTool import AdditionTool
from swarmauri.toolkits.concrete.Toolkit import Toolkit
from swarmauri.agents.concrete.ToolAgent import ToolAgent


@pytest.mark.unit
def test_ubc_resource():
    API_KEY = os.getenv("GROQ_API_KEY")
    llm = GroqToolModel(api_key=API_KEY)
    conversation = Conversation()
    toolkit = Toolkit()
    tool = AdditionTool()
    toolkit.add_tool(tool)

    agent = ToolAgent(llm=llm, conversation=conversation, toolkit=toolkit)
    assert agent.resource == "Agent"


@pytest.mark.unit
def test_ubc_type():
    API_KEY = os.getenv("GROQ_API_KEY")
    llm = GroqToolModel(api_key=API_KEY)
    conversation = Conversation()
    toolkit = Toolkit()
    tool = AdditionTool()
    toolkit.add_tool(tool)

    agent = ToolAgent(llm=llm, conversation=conversation, toolkit=toolkit)
    assert agent.type == "ToolAgent"


@pytest.mark.unit
def test_serialization():
    API_KEY = os.getenv("GROQ_API_KEY")
    llm = GroqToolModel(api_key=API_KEY)
    conversation = Conversation()
    toolkit = Toolkit()
    tool = AdditionTool()
    toolkit.add_tool(tool)

    agent = ToolAgent(llm=llm, conversation=conversation, toolkit=toolkit)
    assert agent.id == ToolAgent.model_validate_json(agent.model_dump_json()).id


@pytest.mark.unit
def test_agent_exec():
    API_KEY = os.getenv("GROQ_API_KEY")
    llm = GroqToolModel(api_key=API_KEY)
    conversation = Conversation()
    toolkit = Toolkit()
    tool = AdditionTool()
    toolkit.add_tool(tool)

    agent = ToolAgent(llm=llm, conversation=conversation, toolkit=toolkit)
    result = agent.exec("Add(512, 671)")
    assert type(result) is str
