import pytest
import os
from swarmauri.llms.concrete.OpenRouterModel import OpenRouterModel as LLM
from swarmauri.conversations.concrete.Conversation import Conversation
from swarmauri.messages.concrete.AgentMessage import AgentMessage
from swarmauri.messages.concrete.HumanMessage import HumanMessage
from swarmauri.messages.concrete.SystemMessage import SystemMessage


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="Skipping due to environment variable not set",
)
@pytest.mark.unit
def test_ubc_resource():
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    llm = LLM(api_key=API_KEY)
    assert llm.resource == "LLM"


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="Skipping due to environment variable not set",
)
@pytest.mark.unit
def test_ubc_type():
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    llm = LLM(api_key=API_KEY)
    assert llm.type == "OpenRouterModel"


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="Skipping due to environment variable not set",
)
@pytest.mark.unit
def test_serialization():
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    llm = LLM(api_key=API_KEY)
    assert llm.id == LLM.model_validate_json(llm.model_dump_json()).id


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="Skipping due to environment variable not set",
)
@pytest.mark.unit
def test_default_name():
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    model = LLM(api_key=API_KEY)
    assert model.name == "mistralai/pixtral-12b:free"


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="Skipping due to environment variable not set",
)
@pytest.mark.unit
def test_no_system_context():
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    model = LLM(api_key=API_KEY)
    conversation = Conversation()

    input_data = "Hello"
    human_message = HumanMessage(content=input_data)
    conversation.add_message(human_message)

    model.predict(conversation=conversation)
    prediction = conversation.get_last().content
    assert type(prediction) == str


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="Skipping due to environment variable not set",
)
@pytest.mark.unit
def test_preamble_system_context():
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    model = LLM(api_key=API_KEY)
    conversation = Conversation()

    system_context = 'You only respond with the following phrase, "Jeff"'
    human_message = SystemMessage(content=system_context)
    conversation.add_message(human_message)

    input_data = "Hi"
    human_message = HumanMessage(content=input_data)
    conversation.add_message(human_message)

    model.predict(conversation=conversation)
    prediction = conversation.get_last().content
    assert type(prediction) == str
    assert "Jeff" in prediction
