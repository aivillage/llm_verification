"""Wrapper around Huggingface."""

from logging import getLogger
from typing import (
    List,
    Dict,
    Optional,
)
import grpclib
from transformers import TextGenerationPipeline, AutoTokenizer, AutoModelForCausalLM

from .base_llm import AbstractLLM
from .llm_rpc.api import GenerateRequest, GenerateReply, LLMTypeRequest, LLMTypeReply
from .schema import Generation, LLMResult, pack_result
from .keystore import ApiKeystore
log = getLogger(__name__)
        
'''
This shouldn't exist, but for some reason the TextGenerationPipeline doesn't work when it's in the normal service class.
'''
class LLMService():
    base_llm: AbstractLLM
    keystore: Optional[ApiKeystore]

    def __init__(self, *, llm: AbstractLLM, keystore: Optional[ApiKeystore] = None):
        self.base_llm = llm
        self.keystore = keystore
        log.debug('Initialized LLMService')

    def check_key(self, api_key: Optional[str]) -> Optional[str]:
        if self.keystore is None:
            return ""
        if api_key is None:
            return None
        return self.keystore.check_key(key=api_key)

    async def Generate(self, stream: "grpclib.server.Stream[GenerateRequest, GenerateReply]") -> None:
        request = await stream.recv_message()
        user = self.check_key(request.api_key)
        if user is None:
            logging.info(f"Invalid API key, {request.api_key}")
            logging.info(f"Valid keys: {self.keystore.get_all_keys()}")
            await stream.send_message(GenerateReply())
            return
        logging.info(f"Generating text for {user}")
        result = self.base_llm.generate(prompts=request.prompts, stop=request.stop)
        reply = pack_result(result)
        await stream.send_message(reply)

    async def GetLlmType(self, stream: "grpclib.server.Stream[LLMTypeRequest, LLMTypeReply]") -> None:
        request = await stream.recv_message()
        user = self.check_key(request.api_key)
        if user is None:
            logging.info(f"Invalid API key, {request.api_key}")
            return stream.send_message(LLMTypeReply())
        logging.info(f"Getting LLM type for {user}")
        msg = LLMTypeReply(llm_type=self.base_llm.llm_name())
        await stream.send_message(msg)

    def __mapping__(self) -> Dict[str, "grpclib.const.Handler"]:
        return {
            "/llm_rpc.api.RemoteLLM/Generate": grpclib.const.Handler(
                self.Generate,
                grpclib.const.Cardinality.UNARY_UNARY,
                GenerateRequest,
                GenerateReply,
            ),
            "/llm_rpc.api.RemoteLLM/GetLlmType": grpclib.const.Handler(
                self.GetLlmType,
                grpclib.const.Cardinality.UNARY_UNARY,
                LLMTypeRequest,
                LLMTypeReply,
            )
        }