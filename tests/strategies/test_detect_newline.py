from io import BytesIO
from unittest.mock import sentinel

import pytest

from scaraplate.strategies import detect_newline


@pytest.mark.parametrize(
    "file_contents, expected_newline",
    [
        # Typical newlines:
        (BytesIO(b"a\na\n"), b"\n"),
        (BytesIO(b"a\r\na\r\n"), b"\r\n"),
        (BytesIO(b"a\ra\r"), b"\r"),
        # Mixed newlines:
        (BytesIO(b"a\r\na\na"), b"\r\n"),
        # Multiple newlines in a row:
        (BytesIO(b"a\n\n\na"), b"\n"),
        (BytesIO(b"\n\n\n"), b"\n"),
        (BytesIO(b"\r\n\r\n"), b"\r\n"),
        (BytesIO(b"\r\n"), b"\r\n"),
        # No newlines:
        (BytesIO(b"a"), sentinel.default),
        (BytesIO(b""), sentinel.default),
        (None, sentinel.default),
    ],
)
def test_detect_newline_single_file(file_contents, expected_newline):
    if file_contents is not None:
        assert file_contents.tell() == 0

    assert expected_newline == detect_newline(file_contents, default=sentinel.default)

    if file_contents is not None:
        assert file_contents.tell() == 0


@pytest.mark.parametrize(
    "file_contents1, file_contents2, expected_newline",
    [
        # One file is missing:
        (None, BytesIO(b"a\n"), b"\n"),
        (BytesIO(b"a\n"), None, b"\n"),
        # Prefer first file having a newline:
        (BytesIO(b"a\n"), BytesIO(b"a\r"), b"\n"),
        (BytesIO(b"a"), BytesIO(b"a\r"), b"\r"),
        # Fallback to default if no file contains a newline:
        (BytesIO(b"a"), BytesIO(b"a"), sentinel.default),
    ],
)
def test_detect_newline_multiple_files(
    file_contents1, file_contents2, expected_newline
):
    if file_contents1 is not None:
        assert file_contents1.tell() == 0
    if file_contents2 is not None:
        assert file_contents2.tell() == 0

    assert expected_newline == detect_newline(
        file_contents1, file_contents2, default=sentinel.default
    )

    if file_contents1 is not None:
        assert file_contents1.tell() == 0
    if file_contents2 is not None:
        assert file_contents2.tell() == 0
