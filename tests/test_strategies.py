import io
from typing import BinaryIO, Optional

import pytest

from scaraplate.strategies import TemplateHash


@pytest.mark.parametrize(
    "template, target, out",
    [
        (
            "hi!",
            None,
            "hi!\n# https://github.com/rambler-digital-solutions/scaraplate template "
            "commit hash: 1111111111111111111111111111111111111111\n",
        ),
        (
            "hi!",
            "ho!",
            "hi!\n# https://github.com/rambler-digital-solutions/scaraplate template "
            "commit hash: 1111111111111111111111111111111111111111\n",
        ),
        (
            "hi!",
            "ho!\n# https://github.com/rambler-digital-solutions/scaraplate template "
            "commit hash: 1111111111111111111111111111111111111111\n",
            "ho!\n# https://github.com/rambler-digital-solutions/scaraplate template "
            "commit hash: 1111111111111111111111111111111111111111\n",
        ),
        (
            "hi!",
            "ho!\n# https://github.com/rambler-digital-solutions/scaraplate template "
            "commit hash: 0000000000000000000000000000000000000000\n",
            "hi!\n# https://github.com/rambler-digital-solutions/scaraplate template "
            "commit hash: 1111111111111111111111111111111111111111\n",
        ),
    ],
)
def test_template_hash(template, target, out):
    if target is not None:
        target_contents: Optional[BinaryIO] = io.BytesIO(target.encode())
    else:
        target_contents = None

    template_contents = io.BytesIO(template.encode())

    strategy = TemplateHash(
        target_contents=target_contents,
        template_contents=template_contents,
        template_commit_hash="1111111111111111111111111111111111111111",
    )

    assert out == strategy.apply().read().decode()
