import yaml
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

CONFIG_PATH = Path("config/agent_llm_config.yaml")

with open(CONFIG_PATH, "r") as f:
    _LLM_CONFIG = yaml.safe_load(f)

_DEFAULTS = _LLM_CONFIG.get("default", {})
_AGENTS   = _LLM_CONFIG.get("agents", {})

def _require_env(var: str) -> str:
    value = os.getenv(var)
    if not value:
        raise EnvironmentError(f"Required environment variable '{var}' is not set")
    return value

ANTHROPIC_API_KEY = _require_env("ANTHROPIC_API_KEY")
OPENAI_API_KEY    = _require_env("OPENAI_API_KEY")



def get_llm(agent_name: str, tools: Optional[list] = None):
    """
    Instantiate and return an LLM for a given agent, optionally with tools bound.
    Useful when you want to manage invocation yourself (e.g. in a LangGraph node).
    """
    agent_cfg = _AGENTS.get(agent_name)
    if not agent_cfg:
        raise ValueError(f"No LLM config found for agent '{agent_name}'")

    model_name = agent_cfg.get("model")
    provider   = agent_cfg.get("provider")

    if not model_name or model_name == "none":
        raise ValueError(f"Agent '{agent_name}' is not allowed to call LLMs")
    if not provider or provider == "none":
        raise ValueError(f"Agent '{agent_name}' requires an LLM provider")
    
    llm = init_chat_model(
        model_name,
        model_provider=provider,
        max_tokens=_DEFAULTS.get("max_output_tokens", 20000),
        temperature=_DEFAULTS.get("temperature", 0.2),
    )
    return llm.bind_tools(tools) if tools else llm


def call_llm(
    *,
    agent_name: str,
    prompt: str,
    tools: Optional[list] = None,
) -> AIMessage:
    """
    Call LLM for a specific agent.
    Always returns the full AIMessage so callers can access:
      - response.content        (text response)
      - response.tool_calls     (tool calls if tools were bound)
    """
    llm      = get_llm(agent_name, tools)
    response = llm.invoke([HumanMessage(content=prompt)])
    return response

def get_text_content(response: AIMessage) -> str:
    """
    Helper to safely extract plain text from an AIMessage.
    Handles both string content and list-of-blocks content (e.g. Anthropic format).
    """
    if isinstance(response.content, str):
        return response.content.strip()
    # Anthropic sometimes returns a list of content blocks
    text_blocks = [b["text"] for b in response.content if isinstance(b, dict) and b.get("type") == "text"]
    return " ".join(text_blocks).strip()