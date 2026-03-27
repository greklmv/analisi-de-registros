import sys
import os

def _setup_vscode_terminal_integration():
    if os.environ.get("TERM_PROGRAM") == "vscode":
        sys.stdout.write("\x1b]633;E;python\x07")
        sys.stdout.flush()

        def _vscode_displayhook(value):
            if value is not None:
                sys.stdout.write("\x1b]633;A\x07")
                sys.__displayhook__(value)
                sys.stdout.write("\x1b]633;B\x07")
            else:
                sys.__displayhook__(value)
        
        if hasattr(sys, 'displayhook'):
            sys.displayhook = _vscode_displayhook

if __name__ == "__main__" or not __name__:
    _setup_vscode_terminal_integration()
    del _setup_vscode_terminal_integration
