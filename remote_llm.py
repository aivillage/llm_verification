"""RESTful API calls to remote LLMs."""
# Standard library imports.
import os
from ast import List
from logging import getLogger

# Third-party imports.
from requests import post, get
from requests.exceptions import HTTPError

log = getLogger(__name__)

def generate_text(preprompt, prompt, model):
    """Generate text from a prompt using the EleutherAI GPT-NeoX-20B model.

    Arguments:
        preprompt: The preprompt to generate text from.
        prompt: The prompt to generate text from.

    Raises:
        ValueError: If the Vanilla Neox API key is not set.
        HTTPError: If the EleutherAI API returns a non-200 HTTP status code.

    Returns:
        str: Text generated by the prompt.
    """
    url = os.environ.get('LLMV_ROUTER_URL')
    if url is None:
        raise ValueError('LLM Verification Router URL is not set')
    route = url
    token = os.environ.get('LLMV_ROUTER_TOKEN')
    if token is None:
        raise ValueError('LLM Verification Router token is not set')
    
    log.info(f'Received text generation request for prompt "{prompt}" for model {model}')
    # Load the Vanilla Neox API key from the config file.

    raw_response = post(url=route,
                        headers={'Authorization': f'Bearer {token}'},
                        json={'prompt': prompt, "preprompt" : preprompt, "model": model})
    
    if raw_response.status_code == 200:
        json_response = raw_response.json()
        if json_response.get('error') is not None:
            log.error(f"Error generating: {json_response['error']}")
            raise HTTPError(
                "Model Error"
            )
        
        return json_response['generation']
    elif 400 <= raw_response.status_code <= 599:
        # ... raise an error.
        raise HTTPError(f'LLM Router API returned error status code {raw_response.status_code}: '
                        f'Response: {raw_response.json()}')
    # ... Otherwise, if it's an unrecognized HTTP status code, then...
    else:
        raise HTTPError(f'LLM Router API returned unrecognized status code {raw_response.status_code}: '
                        f'Response: {raw_response.json()}')


def get_models():
    return ["huggingface", "cohere", "meta", "google", "stability"]

    url = os.environ.get('LLMV_ROUTER_URL')
    if url is None:
        raise ValueError('LLM Verification Router URL is not set')
    route = url + '/models'
    token = os.environ.get('LLMV_ROUTER_TOKEN')
    if token is None:
        raise ValueError('LLM Verification Router token is not set')
    log.info(f"Getting models from {route}")
    raw_response = get(url=route,
                        headers={'Authorization': f'Bearer {token}'})
    
    if raw_response.status_code == 200:
        json_response = raw_response.json()
        if 'error' in json_response:
            log.error(f"Error generating: {json_response['error']}")
            raise HTTPError(
                "Model Error", headers={"Retry-After": str(60000)}
            )
        
        return json_response['models']
    
    elif 400 <= raw_response.status_code <= 599:
        # ... raise an error.
        raise HTTPError(f'LLM Router API returned error status code {raw_response.status_code}: '
                        f'Response: {raw_response.json()}')
    # ... Otherwise, if it's an unrecognized HTTP status code, then...
    else:
        raise HTTPError(f'LLM Router API returned unrecognized status code {raw_response.status_code}: '
                        f'Response: {raw_response.json()}')
    
    