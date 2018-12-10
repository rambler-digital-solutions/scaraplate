from configparser import ConfigParser
from pathlib import Path


def parse_setup_cfg(setup_cfg_path: Path) -> ConfigParser:
    template_parser = ConfigParser()
    template_text = setup_cfg_path.read_text()
    template_parser.read_string(template_text, source=str(setup_cfg_path))
    return template_parser
