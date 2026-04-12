import json
import os
from typing import List, Dict, Any

MEMORY_FILE = "src/ai_knowledge.json"

def load_memory() -> List[str]:
    """Carrega el coneixement après des del fitxer local."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("lessons_learned", [])
    except Exception:
        return []

def save_memory(lessons: List[str]):
    """Guarda el llistat de lliçons apreses."""
    try:
        data = {"lessons_learned": lessons}
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardant memòria IA: {e}")

def add_lesson(lesson: str):
    """Afegeix una nova lliçó a la memòria."""
    lessons = load_memory()
    if lesson not in lessons:
        if len(lessons) > 100: # Limitem la memòria per no saturar el context
            lessons.pop(0)
        lessons.append(lesson)
        save_memory(lessons)

def clear_memory():
    """Neteja tota la memòria apresa."""
    save_memory([])
