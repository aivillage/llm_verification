
"""Wrapper around OpenAI APIs."""
import logging
from typing import (
    Any,
    List,
    Dict,
    Optional,
)
from dataclasses import dataclass
from grpclib.client import Channel

from .llm_rpc.api import RemoteLLMStub, GenerateReplyGenerationList

import asyncio
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

@dataclass
class Generation:
    text: str
    generation_info: Optional[Dict[str, Any]] = None

@dataclass
class LLMResult:
    generations: List[List[Generation]]

logger = logging.getLogger(__name__)

def unpack_generation_list(generations: GenerateReplyGenerationList) -> List[Generation]:
    return [Generation(text=g.text, generation_info=g.generation_info) for g in generations.generations]

class ClientLLM:
    """
    Remote LLM. Uses a GRPC server to generate text.
    """
    client: RemoteLLMStub  #: :meta private:
    
    def __init__(self, **kwargs: Any):
        self.client = RemoteLLMStub(Channel(**kwargs))

    def _generate(
        self, prompts: List[str],
    ) -> LLMResult:
        return loop.run_until_complete(self._agenerate(prompts))

    async def _agenerate(
        self, prompts: List[str],
    ) -> LLMResult:
        """Generate text using the remote llm."""
        result = await self.client.generate(prompts=prompts)
        print(result)
        return LLMResult(generations=[unpack_generation_list(g) for g in result.generations])
