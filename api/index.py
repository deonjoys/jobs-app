import os
import sys

# Add root folder to module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Jobs import app
