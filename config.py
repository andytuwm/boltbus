import json
import os.path

dir_path = os.path.dirname(os.path.realpath(__file__))
try:
    with open(os.path.join(dir_path, "config.json")) as f:
        props = json.load(f)
except:
    props = None
