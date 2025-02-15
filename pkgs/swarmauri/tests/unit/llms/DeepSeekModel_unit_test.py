import pytest
import os
from swarmauri.llms.concrete.DeepSeekModel import DeepSeekModel as LLM
from swarmauri.conversations.concrete.Conversation import Conversation

from swarmauri.messages.concrete.AgentMessage import AgentMessage
from swarmauri.messages.concrete.HumanMessage import HumanMessage
from swarmauri.messages.concrete.SystemMessage import SystemMessage


@pytest.mark.unit
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="Skipping due to environment variable not set",
)
def test_ubc_resource():
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    llm = LLM(api_key=API_KEY)
    assert llm.resource == "LLM"


@pytest.mark.unit
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="Skipping due to environment variable not set",
)
def test_ubc_type():
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    llm = LLM(api_key=API_KEY)
    assert llm.type == "DeepSeekModel"


@pytest.mark.unit
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="Skipping due to environment variable not set",
)
def test_serialization():
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    llm = LLM(api_key=API_KEY)
    assert llm.id == LLM.model_validate_json(llm.model_dump_json()).id


@pytest.mark.unit
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="Skipping due to environment variable not set",
)
def test_default_name():
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    model = LLM(api_key=API_KEY)
    assert model.name == "deepseek-chat"


@pytest.mark.unit
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="Skipping due to environment variable not set",
)
def test_no_system_context():
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    model = LLM(api_key=API_KEY)
    conversation = Conversation()

    input_data = "Hello"
    human_message = HumanMessage(content=input_data)
    conversation.add_message(human_message)

    model.predict(conversation=conversation)
    prediction = conversation.get_last().content
    assert type(prediction) == str


@pytest.mark.unit
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="Skipping due to environment variable not set",
)
def test_preamble_system_context():
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    model = LLM(api_key=API_KEY)
    conversation = Conversation()

    system_context = "Jane knows Martin."
    human_message = SystemMessage(content=system_context)
    conversation.add_message(human_message)

    input_data = "Who does Jane know?"
    human_message = HumanMessage(content=input_data)
    conversation.add_message(human_message)

    model.predict(conversation=conversation)
    prediction = conversation.get_last().content
    assert type(prediction) == str
    assert "martin" in prediction.lower()
