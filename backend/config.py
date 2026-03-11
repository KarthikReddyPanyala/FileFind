import json
import os

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".filefind", "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"folders": []}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def add_folder(folder_path):
    config = load_config()
    if folder_path not in config["folders"]:
        config["folders"].append(folder_path)
        save_config(config)

def get_folders():
    return load_config()["folders"]

def remove_folder(folder_path):
    config = load_config()
    config["folders"] = [f for f in config["folders"] if f != folder_path]
    save_config(config)