import asyncio

import json
from typing import AsyncIterator, Iterator, List, Literal, Dict, Any
import logging

import httpx
from pydantic import PrivateAttr
import requests

from swarmauri.conversations.concrete import Conversation
from swarmauri_core.typing import SubclassUnion

from swarmauri.messages.base.MessageBase import MessageBase
from swarmauri.messages.concrete.AgentMessage import AgentMessage
from swarmauri.messages.concrete.FunctionMessage import FunctionMessage
from swarmauri.llms.base.LLMBase import LLMBase
from swarmauri.schema_converters.concrete.GroqSchemaConverter import (
    GroqSchemaConverter,
)


class GroqToolModel(LLMBase):
    """
    GroqToolModel provides an interface to interact with Groq's large language models for tool usage.

    This class supports synchronous and asynchronous predictions, streaming of responses,
    and batch processing. It communicates with the Groq API to manage conversations, format messages,
    and handle tool-related functions.

    Attributes:
        api_key (str): API key to authenticate with Groq API.
        allowed_models (List[str]): List of permissible model names.
        name (str): Default model name for predictions.
        type (Literal): Type identifier for the model.

    Provider Documentation: https://console.groq.com/docs/tool-use#models
    """

    api_key: str
    allowed_models: List[str] = [
        "llama3-8b-8192",
        "llama3-70b-8192",
        "llama3-groq-70b-8192-tool-use-preview",
        "llama3-groq-8b-8192-tool-use-preview",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        # parallel tool use not supported
        # "mixtral-8x7b-32768",
        # "gemma-7b-it",
        # "gemma2-9b-it",
    ]
    name: str = "llama3-groq-70b-8192-tool-use-preview"
    type: Literal["GroqToolModel"] = "GroqToolModel"
    _headers: Dict[str, str] = PrivateAttr(default=None)
    _api_url: str = PrivateAttr(
        default="https://api.groq.com/openai/v1/chat/completions"
    )

    def __init__(self, **data) -> None:
        """
        Initializes the GroqToolModel instance, setting up headers for API requests.

        Parameters:
            **data: Arbitrary keyword arguments for initialization.
        """
        super().__init__(**data)
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _schema_convert_tools(self, tools) -> List[Dict[str, Any]]:
        """
        Converts toolkit items to API-compatible schema format.

        Parameters:
            tools: Dictionary of tools to be converted.

        Returns:
            List[Dict[str, Any]]: Formatted list of tool dictionaries.
        """
        return [GroqSchemaConverter().convert(tools[tool]) for tool in tools]

    def _format_messages(
        self, messages: List[SubclassUnion[MessageBase]]
    ) -> List[Dict[str, str]]:
        """
        Formats messages for API compatibility.

        Parameters:
            messages (List[MessageBase]): List of message instances to format.

        Returns:
            List[Dict[str, str]]: List of formatted message dictionaries.
        """
        message_properties = ["content", "role", "name", "tool_call_id", "tool_calls"]
        formatted_messages = [
            message.model_dump(include=message_properties, exclude_none=True)
            for message in messages
        ]
        return formatted_messages

    def predict(
        self,
        conversation,
        toolkit=None,
        tool_choice=None,
        temperature=0.7,
        max_tokens=1024,
    ) -> Conversation:
        """
        Makes a synchronous prediction using the Groq model.

        Parameters:
            conversation (Conversation): Conversation instance with message history.
            toolkit: Optional toolkit for tool conversion.
            tool_choice: Tool selection strategy.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum token limit.

        Returns:
            Conversation: Updated conversation with agent responses and tool calls.
        """
        formatted_messages = self._format_messages(conversation.history)

        if toolkit and not tool_choice:
            tool_choice = "auto"

        payload = {
            "model": self.name,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": self._schema_convert_tools(toolkit.tools) if toolkit else [],
            "tool_choice": tool_choice,
        }

        response = requests.post(self._api_url, headers=self._headers, json=payload)
        response.raise_for_status()

        tool_response = response.json()

        if "content" in tool_response["choices"][0]["message"]:
            agent_message = AgentMessage(
                content=tool_response["choices"][0]["message"]["content"]
            )
            conversation.add_message(agent_message)

        tool_calls = tool_response["choices"][0]["message"].get("tool_calls", [])
        if tool_calls:
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]

                func_call = toolkit.get_tool_by_name(func_name)
                func_args = json.loads(tool_call["function"]["arguments"])
                func_result = func_call(**func_args)

                func_message = FunctionMessage(
                    content=json.dumps(func_result),
                    name=func_name,
                    tool_call_id=tool_call["id"],
                )
                conversation.add_message(func_message)

        return conversation

    async def apredict(
        self,
        conversation,
        toolkit=None,
        tool_choice=None,
        temperature=0.7,
        max_tokens=1024,
    ) -> Conversation:
        """
        Makes an asynchronous prediction using the Groq model.

        Parameters:
            conversation (Conversation): Conversation instance with message history.
            toolkit: Optional toolkit for tool conversion.
            tool_choice: Tool selection strategy.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum token limit.

        Returns:
            Conversation: Updated conversation with agent responses and tool calls.
        """
        formatted_messages = self._format_messages(conversation.history)

        if toolkit and not tool_choice:
            tool_choice = "auto"

        payload = {
            "model": self.name,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": self._schema_convert_tools(toolkit.tools) if toolkit else [],
            "tool_choice": tool_choice,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url, headers=self._headers, json=payload
            )
            response.raise_for_status()

        tool_response = response.json()

        if "content" in tool_response["choices"][0]["message"]:
            agent_message = AgentMessage(
                content=tool_response["choices"][0]["message"]["content"]
            )
            conversation.add_message(agent_message)

        tool_calls = tool_response["choices"][0]["message"].get("tool_calls", [])
        if tool_calls:
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]

                func_call = toolkit.get_tool_by_name(func_name)
                func_args = json.loads(tool_call["function"]["arguments"])
                func_result = func_call(**func_args)

                func_message = FunctionMessage(
                    content=json.dumps(func_result),
                    name=func_name,
                    tool_call_id=tool_call["id"],
                )
                conversation.add_message(func_message)

        logging.info(conversation.history)
        return conversation

    def stream(
        self,
        conversation: Conversation,
        toolkit=None,
        tool_choice=None,
        temperature=0.7,
        max_tokens=1024,
    ) -> Iterator[str]:
        """
        Streams response from Groq model in real-time.

        Parameters:
            conversation (Conversation): Conversation instance with message history.
            toolkit: Optional toolkit for tool conversion.
            tool_choice: Tool selection strategy.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum token limit.

        Yields:
            Iterator[str]: Streamed response content.
        """

        formatted_messages = self._format_messages(conversation.history)

        request_data = {
            "model": self.name,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": self._schema_convert_tools(toolkit.tools) if toolkit else [],
            "tool_choice": tool_choice or "auto",
        }

        # Initial tool response
        response = requests.post(
            self._api_url,
            headers=self._headers,
            json=request_data,
        )
        response.raise_for_status()
        tool_response = response.json()
        logging.info(tool_response)

        if "content" in tool_response["choices"][0]["message"]:
            agent_message = AgentMessage(
                content=tool_response["choices"][0]["message"]["content"]
            )
            conversation.add_message(agent_message)

        tool_calls = tool_response["choices"][0]["message"].get("tool_calls", [])
        if tool_calls:
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]

                func_call = toolkit.get_tool_by_name(func_name)
                func_args = json.loads(tool_call["function"]["arguments"])
                func_result = func_call(**func_args)

                func_message = FunctionMessage(
                    content=json.dumps(func_result),
                    name=func_name,
                    tool_call_id=tool_call["id"],
                )
                conversation.add_message(func_message)

        formatted_messages = self._format_messages(conversation.history)
        request_data["messages"] = formatted_messages
        request_data["stream"] = True
        request_data.pop("tools", None)
        request_data.pop("tool_choice", None)

        with requests.post(
            self._api_url,
            headers=self._headers,
            json=request_data,
        ) as response:
            response.raise_for_status()
            message_content = ""

            for line in response.iter_lines(decode_unicode=True):
                json_str = line.replace('data: ', '')
                try:
                    if json_str:
                        chunk = json.loads(json_str)
                        if chunk["choices"][0]["delta"]:
                            delta = chunk["choices"][0]["delta"]["content"]
                            message_content += delta
                            yield delta
                except json.JSONDecodeError:
                    pass

            conversation.add_message(AgentMessage(content=message_content))

    async def astream(
        self,
        conversation,
        toolkit=None,
        tool_choice=None,
        temperature=0.7,
        max_tokens=1024,
    ) -> AsyncIterator[str]:
        """
        Asynchronously streams response from Groq model.

        Parameters:
            conversation (Conversation): Conversation instance with message history.
            toolkit: Optional toolkit for tool conversion.
            tool_choice: Tool selection strategy.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum token limit.

        Yields:
            AsyncIterator[str]: Streamed response content.
        """
        formatted_messages = self._format_messages(conversation.history)
    
        request_data = {
            "model": self.name,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": self._schema_convert_tools(toolkit.tools) if toolkit else [],
            "tool_choice": tool_choice or "auto",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                headers=self._headers,
                json=request_data
            )
            response.raise_for_status()
            tool_response = response.json()
            logging.info(tool_response)

            if "content" in tool_response["choices"][0]["message"]:
                agent_message = AgentMessage(
                    content=tool_response["choices"][0]["message"]["content"]
                )
                conversation.add_message(agent_message)

            tool_calls = tool_response["choices"][0]["message"].get("tool_calls", [])
            if tool_calls:
                for tool_call in tool_calls:
                    func_name = tool_call["function"]["name"]

                    func_call = toolkit.get_tool_by_name(func_name)
                    func_args = json.loads(tool_call["function"]["arguments"])
                    func_result = func_call(**func_args)

                    func_message = FunctionMessage(
                        content=json.dumps(func_result),
                        name=func_name,
                        tool_call_id=tool_call["id"],
                    )
                    conversation.add_message(func_message)

            formatted_messages = self._format_messages(conversation.history)
            request_data["messages"] = formatted_messages
            request_data["stream"] = True
            request_data.pop("tools", None)
            request_data.pop("tool_choice", None)

            async with httpx.AsyncClient() as client:
                response = await client.post(self._api_url, headers=self._headers, json=request_data)

                response.raise_for_status()
                message_content = ""

            async for line in response.aiter_lines():
                json_str = line.replace('data: ', '')
                try:
                    if json_str:
                        chunk = json.loads(json_str)
                        if chunk["choices"][0]["delta"]:
                            delta = chunk["choices"][0]["delta"]["content"]
                            message_content += delta
                            yield delta
                except json.JSONDecodeError:
                    pass
        conversation.add_message(AgentMessage(content=message_content))

    def batch(
        self,
        conversations: List[Conversation],
        toolkit=None,
        tool_choice=None,
        temperature=0.7,
        max_tokens=1024,
    ) -> List[Conversation]:
        """
        Processes a batch of conversations and generates responses for each sequentially.

        Args:
            conversations (List[Conversation]): List of conversations to process.
            temperature (float): Sampling temperature for response diversity.
            max_tokens (int): Maximum tokens for each response.
            top_p (float): Cumulative probability for nucleus sampling.
            enable_json (bool): Whether to format the response as JSON.
            stop (Optional[List[str]]): List of stop sequences for response termination.

        Returns:
            List[Conversation]: List of updated conversations with model responses.
        """
        if toolkit and not tool_choice:
            tool_choice = "auto"

        return [
            self.predict(
                conv,
                toolkit=toolkit,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            for conv in conversations
        ]

    async def abatch(
        self,
        conversations: List[Conversation],
        toolkit=None,
        tool_choice=None,
        temperature=0.7,
        max_tokens=1024,
        max_concurrent=5,
    ) -> List[Conversation]:
        """
        Async method for processing a batch of conversations concurrently.

        Args:
            conversations (List[Conversation]): List of conversations to process.
            temperature (float): Sampling temperature for response diversity.
            max_tokens (int): Maximum tokens for each response.
            top_p (float): Cumulative probability for nucleus sampling.
            enable_json (bool): Whether to format the response as JSON.
            stop (Optional[List[str]]): List of stop sequences for response termination.
            max_concurrent (int): Maximum number of concurrent requests.

        Returns:
            List[Conversation]: List of updated conversations with model responses.
        """
        if toolkit and not tool_choice:
            tool_choice = "auto"

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_conversation(conv) -> Conversation:
            async with semaphore:
                return await self.apredict(
                    conv,
                    toolkit=toolkit,
                    tool_choice=tool_choice,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

        tasks = [process_conversation(conv) for conv in conversations]
        return await asyncio.gather(*tasks)
