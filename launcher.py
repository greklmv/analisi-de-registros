import os
import sys
import streamlit.web.cli as stcli

def main():
    # PyInstaller extrae los archivos en un directorio temporal en sys._MEIPASS para --onefile
    # Para --onedir, sys.executable apunta al ejecutable. Los datos están en _internal.
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        
    internal_dir = os.path.join(base_dir, '_internal')
    if os.path.exists(internal_dir):
        os.chdir(internal_dir)
    else:
        os.chdir(base_dir)
    
    # Asegurar que se abra el navegador local
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "false"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    # Forzar puerto y dirección para evitar conflictos (ej. variables PORT=3000 de desarrollo en macOS)
    os.environ["STREAMLIT_SERVER_PORT"] = "8501"
    os.environ["PORT"] = "8501"
    
    # El archivo app.py debe estar dentro de la carpeta actual gracias al chdir
    sys.argv = ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "localhost"]
    
    try:
        sys.exit(stcli.main())
    except Exception as e:
        print(f"Error fatal: {e}")
        input("Presiona Enter para salir...")
        sys.exit(1)

if __name__ == "__main__":
    main()
