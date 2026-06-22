import os
import requests
import json
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterError(Exception):
    """Error tipat per a fallades de la integració amb OpenRouter."""
    pass


class MissingApiKeyError(OpenRouterError):
    """No hi ha cap API key configurada (ni .env ni kilo.json)."""
    pass


class ApiCallError(OpenRouterError):
    """La crida HTTP a OpenRouter ha fallat (xarxa, 4xx/5xx, timeout...)."""
    pass


def _resolve_api_key() -> str:
    """Troba la API key des de .env (prioritat) o kilo.json (fallback local)."""
    api_key = OPENROUTER_API_KEY
    if api_key:
        return api_key

    # Fallback: kilo.json (només per a ús local)
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        kilo_path = os.path.join(base_dir, "kilo.json")
        if os.path.exists(kilo_path):
            with open(kilo_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            api_key = data.get("provider", {}).get("openrouter", {}) \
                        .get("options", {}).get("apiKey")
    except Exception:
        api_key = None

    if not api_key or "YOUR_" in api_key:
        raise MissingApiKeyError(
            "No s'ha trobat OPENROUTER_API_KEY. "
            "Configura-la a .env (OPENROUTER_API_KEY=sk-or-v1-...) "
            "o a kilo.json."
        )
    return api_key


def call_openrouter(
    messages: List[Dict[str, str]],
    model: str = "deepseek/deepseek-chat",
    max_tokens: int = 1500,
    temperature: float = 0.3, # Baixem temperatura per a anàlisi tècnica més precisa
    **kwargs,
) -> Dict[str, Any]:
    """
    Crida l'API d'OpenRouter.
    Sempre retorna el JSON si tot va bé; en cas contrari llança OpenRouterError.
    """
    api_key = _resolve_api_key()

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
    except requests.exceptions.HTTPError as e:
        raise ApiCallError(
            f"OpenRouter ha retornat un error HTTP ({response.status_code}): {e}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise ApiCallError("Timeout (90s) contactant amb OpenRouter.") from e
    except requests.exceptions.RequestException as e:
        raise ApiCallError(f"Error de xarxa contactant amb OpenRouter: {e}") from e


def analyze_with_ai(
    context: str,
    user_question: str,
    memory: Optional[List[str]] = None,
    model: str = "deepseek/deepseek-chat"
) -> str:
    """
    Analitza el registre amb la IA. Sempre retorna text; si falla,
    llança OpenRouterError perquè la UI la pugui mostrar a l'usuari.
    """

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
        system_prompt += f"\nCONEIXEMENT APRÈS (LESSONS LEARNED):\n{knowledge_str}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": f"Entès. Tinc el context de les dades de telemetria:\n{context}"},
        {"role": "user", "content": user_question},
    ]

    result = call_openrouter(messages, model=model)
    if "choices" not in result or not result["choices"]:
        raise ApiCallError(f"Resposta inesperada d'OpenRouter: {result}")
    return result["choices"][0]["message"]["content"]
