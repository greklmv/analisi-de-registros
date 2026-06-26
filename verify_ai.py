import sys
import os

# Al estar en la raíz del proyecto, podemos importar de 'src' directamente
from src.openrouter_client import analyze_with_ai
from src.ai_memory import add_lesson, load_memory, clear_memory

def test_ai_system():
    # Usar un archivo de memoria temporal para no borrar el conocimiento real
    import src.ai_memory
    src.ai_memory.MEMORY_FILE = "mock_memory_test.json"
    
    print("--- Test 1: Memòria i Aprenentatge ---")
    clear_memory()
    add_lesson("Al PK 12.5 el límit de velocitat és de 95 km/h per proves especials.")
    memory = load_memory()
    print(f"Memòria carregada: {memory}")
    
    print("\n--- Test 2: Crida a OpenRouter (Mock Context) ---")
    context = """### RESUM EXECUTIU (KPIs)
- Unitat: UT 114.22
- Distància total: 5.2 km
- Velocitat màxima: 92.5 km/h
- Durada: 450 segons
- Anomalies detectades: Excés Velocitat

### CRONOLOGIA D'ESDEVENIMENTS
- 09:15:30 | Sortida (ATO) de Pl. Catalunya
- 09:17:45 | 🚀 SOBREVELOCITAT | Velocitat màxima de 92.5 km/h (Límit 90) al PK 12.510.
"""
    
    question = "He de preocupar-me per aquesta sobrevelocitat al PK 12.5?"
    
    try:
        response = analyze_with_ai(context, question, memory=memory)
        print(f"Resposta de l'IA:\n{response}")
    except Exception as e:
        print(f"Error en la crida: {e}")

if __name__ == "__main__":
    test_ai_system()
