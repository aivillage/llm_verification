
import abc
from typing import List, Optional

from remote_llm.schema import LLMResult

class AbstractLLM(object):
    @abc.abstractmethod
    def llm_name(self) -> str:
        pass

    @abc.abstractmethod
    def generate(self, prompts: List[str], stop: Optional[List[str]] = None) -> LLMResult:
        pass

