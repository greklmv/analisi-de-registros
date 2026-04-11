import os
import requests
from typing import Optional, List, Dict, Any

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def call_openrouter(
    messages: List[Dict[str, str]],
    model: str = "deepseek/deepseek-chat",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    **kwargs,
) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://analisi-de-registros.streamlit.app",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        **kwargs,
    }

    try:
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}")
        return None


def analyze_with_ai(
    context: str, user_question: str, model: str = "deepseek/deepseek-chat"
) -> Optional[str]:
    messages = [
        {
            "role": "system",
            "content": "Ets un assistent expert en anàlisi de registres ferroviaris. Analitzes dades de trens FGC i proporciones conclusions tècniques precises.",
        },
        {"role": "system", "content": f"Context de les dades:\n{context}"},
        {"role": "user", "content": user_question},
    ]

    result = call_openrouter(messages, model=model)
    if result and "choices" in result:
        return result["choices"][0]["message"]["content"]
    return None
