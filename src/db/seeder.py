import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from hives.core.database import seed_database

'''
Función que crea la base de datos con la estructura inicial
'''
if __name__ == "__main__":
    seed_database()
