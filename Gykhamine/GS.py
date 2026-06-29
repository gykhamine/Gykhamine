#!/usr/bin/env python3
"""Point d'entrée principal de Gykhamine Studio"""
import sys
from gykhamine_studio.app import GykhamineStudioApp

def gy():
    app = GykhamineStudioApp()
    sys.exit(app.run(sys.argv))

if __name__ == "__main__":
    gy()
