import os
import sys
import streamlit.web.cli as stcli

def main():
    # PyInstaller extrae los archivos en un directorio temporal en sys._MEIPASS
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    
    # Asegurar que se abra el navegador local
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "false"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    # Inyectar argumentos para streamlit
    sys.argv = ["streamlit", "run", "app.py"]
    
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
