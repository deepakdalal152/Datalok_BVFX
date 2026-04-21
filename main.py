import sys
import os
import json
import inspect
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from project_browser import ProjectBrowser
from datetime import datetime

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
 

# --- LICENSE CHECK ---
def check_license(config):
    # expiry_str = config.get("LICENSE_EXPIRY","2025-05-17")
    expiry_str = "2026-05-30"
    if not expiry_str:
        logging.warning("No LICENSE_EXPIRY found in config.")
        sys.exit(1)
        return

    today = datetime.now().date()
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    if today > expiry:
        logging.error("License expired on %s.", expiry_str)
        QMessageBox.critical(
            None, "License Expired", "License has expired. Please contact support."
        )
        sys.exit(1)


# ----------------------


def get_config_path():
    if getattr(sys, "frozen", False):  # If running from EXE (PyInstaller bundled)
        base_path = os.getenv("DATALOK", os.path.dirname(sys.executable))
    else:  # Running as a normal script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "config.json")

 
def load_config():
    config_path = get_config_path()
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    config = normalize_paths(config)

    # Make TEMPLATE_PATH absolute relative to config file
    config_dir = os.path.dirname(config_path)
    if "TEMPLATE_PATH" in config and not os.path.isabs(config["TEMPLATE_PATH"]):
        config["TEMPLATE_PATH"] = os.path.normpath(
            os.path.join(config_dir, config["TEMPLATE_PATH"])
        )

    return config


def normalize_paths(config):
    def normalize(value):
        if isinstance(value, str):
            return value.replace("\\", "/")
        elif isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items()}
        else:
            return value

    return {key: normalize(value) for key, value in config.items()}


def show_error_and_exit(message):
    logging.exception("Startup error: %s", message)
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("Configuration Error")
    msg_box.setText("Failed to load configuration.")
    msg_box.setInformativeText(message)
    msg_box.exec()
    sys.exit(1)


def main():
    app = QApplication(sys.argv)

    try:
        config = load_config()
        check_license(config)
    except Exception as e:
        show_error_and_exit(str(e))

    browser = ProjectBrowser(config=config)
    browser.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
