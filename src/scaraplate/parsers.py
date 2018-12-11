import io
from collections import OrderedDict
from configparser import ConfigParser
from pathlib import Path
from typing import BinaryIO


def setup_cfg_parser_from_path(setup_cfg_path: Path) -> ConfigParser:
    parser = ConfigParser()
    text = setup_cfg_path.read_text()
    parser.read_string(text, source=str(setup_cfg_path))
    return parser


def pylintrc_parser(data: BinaryIO, source: str) -> ConfigParser:
    parser = ConfigParser()
    text = data.read().decode()
    parser.read_string(text, source=source)
    return parser


def parser_to_pretty_output(parser: ConfigParser) -> BinaryIO:
    parser = _sorted_configparser(parser)

    buffer = io.StringIO()
    parser.write(buffer)
    content = buffer.getvalue().replace("\t", " " * 4)

    acc = []
    for line in content.splitlines():
        acc.append(line.rstrip())
    text = "\n".join(acc)
    return io.BytesIO(text.encode())


def _sorted_configparser(parser: ConfigParser) -> ConfigParser:
    out = ConfigParser(dict_type=OrderedDict)  # type: ignore
    out.read_dict(parser)
    for section in out._sections:  # type: ignore
        section_ = OrderedDict(sorted(out._sections[section].items()))  # type: ignore
        out._sections[section] = section_  # type: ignore

    out._sections = OrderedDict(sorted(out._sections.items()))  # type: ignore
    return out
