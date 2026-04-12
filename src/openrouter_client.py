import os
import requests
import json
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

def call_openrouter(
    messages: List[Dict[str, str]],
    model: str = "deepseek/deepseek-chat",
    max_tokens: int = 1500,
    temperature: float = 0.3, # Baixem temperatura per a anàlisi tècnica més precisa
    **kwargs,
) -> Optional[Dict[str, Any]]:
    # Intentem agafar la clau de l'entorn, si no, mirem si està a kilo.json (local o global)
    api_key = OPENROUTER_API_KEY
    if not api_key:
        api_key = "" # Require API key from environment or .env

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://analisi-de-registros.streamlit.app",
        "X-Title": "FGC OTMR Analyst",
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
            timeout=90,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}")
        return None

def analyze_with_ai(
    context: str, 
    user_question: str, 
    memory: Optional[List[str]] = None,
    model: str = "deepseek/deepseek-chat"
) -> Optional[str]:
    
    system_prompt = """Ets un analista expert en seguretat ferroviària i telemetria d'OTMR per a FGC (Ferrocarrils de la Generalitat de Catalunya).
La teva missió és analitzar dades tècniques (PKs, velocitats, estats de tracció, fre d'urgència, etc.) i proporcionar conclusions precises.

NORMES:
1. Respon exclusivament basant-te en les dades proporcionades.
2. Si detectes una anomalia (sobrevelocitat, frenada brusca), indica el PK aproximat i la senyal propera si apareix.
3. Utilitza terminologia tècnica de FGC (Via 1/2, Ascendent/Descendent, ATP, ATO, Bolet, etc.).
4. Sigues concís i professional.
5. NO inventis dades que no estiguin al context.
"""

    if memory:
        knowledge_str = "\n".join([f"- {item}" for item in memory])
        system_prompt += f"\nCONEIXEMENT APRÈS (LEASSONS LEARNED):\n{knowledge_str}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": f"Entès. Tinc el context de les dades de telemetria:\n{context}"},
        {"role": "user", "content": user_question},
    ]

    result = call_openrouter(messages, model=model)
    if result and "choices" in result:
        return result["choices"][0]["message"]["content"]
    return None
