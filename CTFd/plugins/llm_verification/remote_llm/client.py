"""Wrapper around Huggingface."""
from logging import getLogger
from typing import List, Optional

import asyncio
from grpclib.client import Channel

from .llm_rpc.api import RemoteLLMStub, GenerateReplyGenerationList
from .schema import Generation, LLMResult


try:
    loop = asyncio.get_event_loop()
except RuntimeError as e:
    if str(e).startswith('There is no current event loop in thread'):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        raise
import nest_asyncio
nest_asyncio.apply()

log = getLogger(__name__)

def unpack_generation_list(generations: GenerateReplyGenerationList) -> List[Generation]:
    return [Generation(text=g.text, generation_info=g.generation_info) for g in generations.generations]

class ClientLLM:
    """
    Remote LLM. Uses a GRPC server to generate text.
    """
    host: str
    port: int
    api_key: str = None
    channel_kwargs: Optional[dict] = None
    
    def __init__(
        self,
        host: str,
        port: int,
        api_key: str = None,
        channel_kwargs: Optional[dict] = None,
    ):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.channel_kwargs = channel_kwargs or {}
        log.debug('Initialized ClientLLM.')

    async def generate_text(
        self, prompts: List[str], stop: Optional[List[str]] = None
    ) -> LLMResult:
        """Generate text using the remote llm."""
        async with Channel(self.host, self.port, **self.channel_kwargs) as channel:
            client = RemoteLLMStub(channel)
            result = await client.generate(prompts=prompts, stop=stop, api_key=self.api_key)
            return LLMResult(generations=[unpack_generation_list(g) for g in result.generations])
    
    async def llm_name(self) -> str:
        """Get model info."""
        async with Channel(self.host, self.port, **self.channel_kwargs) as channel:
            client = RemoteLLMStub(channel)
            result = await client.get_llm_type(api_key=self.api_key)
            return result.llm_type
    
    def sync_generate_text(
        self, prompts: List[str],
    ) -> LLMResult:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            if str(e).startswith('There is no current event loop in thread'):
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise

        return loop.run_until_complete(self.generate_text(prompts))
    
    def sync_llm_name(self) -> str:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            if str(e).startswith('There is no current event loop in thread'):
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise
        return loop.run_until_complete(self.llm_name())