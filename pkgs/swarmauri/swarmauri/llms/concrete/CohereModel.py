import json
import asyncio
import time
from typing import List, Dict, Literal, AsyncIterator, Iterator
from pydantic import Field
import requests
import aiohttp
from swarmauri_core.typing import SubclassUnion

from swarmauri.messages.base.MessageBase import MessageBase
from swarmauri.messages.concrete.AgentMessage import AgentMessage
from swarmauri.llms.base.LLMBase import LLMBase
from swarmauri.messages.concrete.AgentMessage import UsageData
from swarmauri.utils.duration_manager import DurationManager


class CohereModel(LLMBase):
    """
    This class provides both synchronous and asynchronous methods for interacting with
    Cohere's chat endpoints, supporting single messages, streaming, and batch processing.

    Attributes:
        api_key (str): The authentication key for accessing Cohere's API.
        allowed_models (List[str]): List of supported Cohere model identifiers.
        name (str): The default model name to use (defaults to "command").
        type (Literal["CohereModel"]): The type identifier for this model class.
        base_url (str): The base URL for Cohere's API endpoints.
        headers (Dict[str, str]): HTTP headers used for API requests.

    API Reference: https://docs.cohere.com/reference/chat
    Link to API Key: https://dashboard.cohere.com/api-keys
    """

    api_key: str
    allowed_models: List[str] = [
        "command",
        "command-r-plus-08-2024",
        "command-r-plus-04-2024",
        "command-r-03-2024",
        "command-r-08-2024",
        "command-light",
    ]
    name: str = "command"
    type: Literal["CohereModel"] = "CohereModel"
    base_url: str = Field(default="https://api.cohere.ai/v1")
    headers: Dict[str, str] = Field(default=None, exclude=True)

    def __init__(self, **data):
        """
        Initialize the CohereModel with the provided configuration.

        Args:
            **data: Keyword arguments for model configuration, must include 'api_key'.
        """
        super().__init__(**data)
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}",
        }

    def _format_messages(
        self, messages: List[SubclassUnion[MessageBase]]
    ) -> tuple[List[Dict[str, str]], str, str]:
        """
        Format a list of messages into Cohere's expected chat format.

        Args:
            messages: List of MessageBase objects containing the conversation history.

        Returns:
            tuple containing:
                - List[Dict[str, str]]: Formatted chat history
                - str: System message (if any)
                - str: Latest user message
        """
        chat_history = []
        system_message = None
        user_message = None

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            elif msg.role == "human":
                user_message = msg.content
            elif msg.role == "assistant" and len(chat_history) > 0:
                last_entry = chat_history[-1]
                last_entry["text"] = msg.content
            elif msg.role == "human" and user_message != msg.content:
                chat_history.append(
                    {
                        "user_name": "Human",
                        "message": msg.content,
                        "text": "",
                    }
                )

        chat_history = [h for h in chat_history if h["text"]]

        return chat_history, system_message, user_message

    def _prepare_usage_data(
        self,
        usage_data: Dict,
        prompt_time: float,
        completion_time: float,
    ) -> UsageData:
        """
        Prepare usage statistics from API response and timing data.

        Args:
            usage_data: Dictionary containing token usage information from the API
            prompt_time: Time taken to send the prompt
            completion_time: Time taken to receive the completion

        Returns:
            UsageData: Object containing formatted usage statistics
        """
        total_time = prompt_time + completion_time

        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens

        usage = UsageData(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=total_tokens,
            prompt_time=prompt_time,
            completion_time=completion_time,
            total_time=total_time,
        )
        return usage

    def predict(self, conversation, temperature=0.7, max_tokens=256):
        """
        Generate a single prediction from the model synchronously.

        Args:
            conversation: The conversation object containing message history
            temperature (float, optional): Sampling temperature. Defaults to 0.7
            max_tokens (int, optional): Maximum tokens in response. Defaults to 256

        Returns:
            The updated conversation object with the model's response added

        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        chat_history, system_message, message = self._format_messages(
            conversation.history
        )

        if not message:
            if conversation.history:
                message = conversation.history[-1].content
            else:
                message = ""

        payload = {
            "message": message,
            "chat_history": chat_history,
            "model": self.name,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_message:
            payload["preamble"] = system_message

        with DurationManager() as prompt_timer:
            response = requests.post(
                f"{self.base_url}/chat", headers=self.headers, json=payload
            )
            response.raise_for_status()
            data = response.json()

        with DurationManager() as completion_timer:
            message_content = data["text"]

        usage_data = data.get("usage", {})

        usage = self._prepare_usage_data(
            usage_data, prompt_timer.duration, completion_timer.duration
        )

        conversation.add_message(AgentMessage(content=message_content, usage=usage))
        return conversation

    async def apredict(self, conversation, temperature=0.7, max_tokens=256):
        """
        Generate a single prediction from the model asynchronously.

        Args:
            conversation: The conversation object containing message history
            temperature (float, optional): Sampling temperature. Defaults to 0.7
            max_tokens (int, optional): Maximum tokens in response. Defaults to 256

        Returns:
            The updated conversation object with the model's response added

        Raises:
            Exception: If the API request fails
        """
        chat_history, system_message, message = self._format_messages(
            conversation.history
        )

        if not message:
            if conversation.history:
                message = conversation.history[-1].content
            else:
                message = ""

        payload = {
            "message": message,
            "chat_history": chat_history,
            "model": self.name,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_message:
            payload["preamble"] = system_message

        async with aiohttp.ClientSession() as session:
            with DurationManager() as prompt_timer:
                async with session.post(
                    f"{self.base_url}/chat", headers=self.headers, json=payload
                ) as response:
                    if response.status != 200:
                        raise Exception(
                            f"API request failed with status {response.status}"
                        )
                    data = await response.json()

            with DurationManager() as completion_timer:
                message_content = data["text"]

            usage_data = data.get("usage", {})

            usage = self._prepare_usage_data(
                usage_data, prompt_timer.duration, completion_timer.duration
            )

            conversation.add_message(AgentMessage(content=message_content, usage=usage))
            return conversation

    def stream(self, conversation, temperature=0.7, max_tokens=256) -> Iterator[str]:
        """
        Stream predictions from the model synchronously.

        Args:
            conversation: The conversation object containing message history
            temperature (float, optional): Sampling temperature. Defaults to 0.7
            max_tokens (int, optional): Maximum tokens in response. Defaults to 256

        Yields:
            str: Chunks of the generated text as they become available

        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        chat_history, system_message, message = self._format_messages(
            conversation.history
        )

        if not message and conversation.history:
            message = conversation.history[-1].content

        payload = {
            "message": message or "",
            "chat_history": chat_history,
            "model": self.name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if system_message:
            payload["preamble"] = system_message

        collected_content = []
        usage_data = {}

        with DurationManager() as prompt_timer:
            with requests.post(
                f"{self.base_url}/chat", headers=self.headers, json=payload, stream=True
            ) as response:
                response.raise_for_status()

                with DurationManager() as completion_timer:
                    for line in response.iter_lines():
                        if line:
                            chunk = json.loads(line.decode("utf-8"))
                            if "text" in chunk:
                                content = chunk["text"]
                                collected_content.append(content)
                                yield content
                            elif "usage" in chunk:
                                usage_data = chunk["usage"]

        full_content = "".join(collected_content)
        usage = self._prepare_usage_data(
            usage_data, prompt_timer.duration, completion_timer.duration
        )

        conversation.add_message(AgentMessage(content=full_content, usage=usage))

    async def astream(
        self, conversation, temperature=0.7, max_tokens=256
    ) -> AsyncIterator[str]:
        """
        Stream predictions from the model asynchronously.

        Args:
            conversation: The conversation object containing message history
            temperature (float, optional): Sampling temperature. Defaults to 0.7
            max_tokens (int, optional): Maximum tokens in response. Defaults to 256

        Yields:
            str: Chunks of the generated text as they become available

        Raises:
            Exception: If the API request fails
        """
        chat_history, system_message, message = self._format_messages(
            conversation.history
        )

        if not message:
            if conversation.history:
                message = conversation.history[-1].content
            else:
                message = ""

        payload = {
            "message": message,
            "chat_history": chat_history,
            "model": self.name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if system_message:
            payload["preamble"] = system_message

        collected_content = []
        usage_data = {}

        async with aiohttp.ClientSession() as session:
            with DurationManager() as prompt_timer:
                async with session.post(
                    f"{self.base_url}/chat", headers=self.headers, json=payload
                ) as response:
                    if response.status != 200:
                        raise Exception(
                            f"API request failed with status {response.status}"
                        )

                    with DurationManager() as completion_timer:
                        async for line in response.content:
                            if line:
                                chunk = json.loads(line.decode("utf-8"))
                                if "text" in chunk:
                                    content = chunk["text"]
                                    collected_content.append(content)
                                    yield content
                                elif "usage" in chunk:
                                    usage_data = chunk["usage"]
                            await asyncio.sleep(0)

            full_content = "".join(collected_content)
            usage = self._prepare_usage_data(
                usage_data, prompt_timer.duration, completion_timer.duration
            )

            conversation.add_message(AgentMessage(content=full_content, usage=usage))

    def batch(self, conversations: List, temperature=0.7, max_tokens=256) -> List:
        """
        Process multiple conversations synchronously.

        Args:
            conversations: List of conversation objects to process
            temperature (float, optional): Sampling temperature. Defaults to 0.7
            max_tokens (int, optional): Maximum tokens in response. Defaults to 256

        Returns:
            List of updated conversation objects with model responses added
        """
        return [
            self.predict(conv, temperature=temperature, max_tokens=max_tokens)
            for conv in conversations
        ]

    async def abatch(
        self, conversations: List, temperature=0.7, max_tokens=256, max_concurrent=5
    ) -> List:
        """
        Process multiple conversations asynchronously with concurrency control.

        Args:
            conversations: List of conversation objects to process
            temperature (float, optional): Sampling temperature. Defaults to 0.7
            max_tokens (int, optional): Maximum tokens in response. Defaults to 256
            max_concurrent (int, optional): Maximum number of concurrent requests. Defaults to 5

        Returns:
            List of updated conversation objects with model responses added
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_conversation(conv):
            async with semaphore:
                return await self.apredict(
                    conv, temperature=temperature, max_tokens=max_tokens
                )

        tasks = [process_conversation(conv) for conv in conversations]
        return await asyncio.gather(*tasks)
