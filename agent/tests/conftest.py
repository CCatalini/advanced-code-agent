import os
import sys

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(AGENT_DIR, "..", ".env"))
