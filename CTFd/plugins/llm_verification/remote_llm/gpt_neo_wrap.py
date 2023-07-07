"""Wrapper around Huggingface."""
from typing import List, Optional
from transformers import TextGenerationPipeline, AutoTokenizer, AutoModelForCausalLM

from .base_llm import AbstractLLM
from .schema import Generation, LLMResult
from logging import getLogger


log = getLogger(__name__)

class GPTNeoWrap(AbstractLLM):
    log.debug('Initialized GTNeoWrap')
    model: AutoModelForCausalLM
    tokenizer: AutoTokenizer
    generator: TextGenerationPipeline
    max_length: int 
    num_sequences: int

    def __init__(self, *, model: AutoModelForCausalLM, tokenizer: AutoTokenizer, max_length: int = 100, num_sequences: int = 1):
        self.model = model
        self.tokenizer = tokenizer
        self.generator = TextGenerationPipeline(model=model, tokenizer=tokenizer, device=0)
        self.max_length = max_length
        self.num_sequences = num_sequences

    def generate(self, prompts: List[str], stop: Optional[List[str]] = None) -> LLMResult:
        generations = []
        for prompt in prompts:
            generated = self.generator(
                prompt,
                max_length=self.max_length,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                num_return_sequences=self.num_sequences,
                repetition_penalty=1.2,
                temperature=1.0,
                no_repeat_ngram_size=3,
            )
            generated = [Generation(text=gen['generated_text'][len(prompt):]) for gen in generated]
            generations.append(generated)
        return LLMResult(generations=generations)
    
    def llm_name(self) -> str:
        return self.model.config._name_or_path