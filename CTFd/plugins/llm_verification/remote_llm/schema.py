try:
    from langchain.schema import Generation, LLMResult
    __all__ = ['Generation', 'LLMResult']
except ImportError:
    from dataclasses import dataclass
    from typing import Any, List, Dict, Optional
    
    @dataclass
    class Generation:
        text: str
        generation_info: Optional[Dict[str, Any]] = None

    @dataclass
    class LLMResult:
        generations: List[List[Generation]]

from .llm_rpc.api import GenerateReply, GenerateReplyGeneration, GenerateReplyGenerationList

def unpack_result(result: GenerateReply) -> LLMResult:
    return LLMResult(generations=[[Generation(text=gg.text, generation_info=gg.generation_info) for gg in g.generations] for g in result.generations])

def pack_result(result: LLMResult) -> GenerateReply:
    return GenerateReply(generations=[GenerateReplyGenerationList(generations=[GenerateReplyGeneration(text=gg.text, generation_info=gg.generation_info) for gg in g]) for g in result.generations])