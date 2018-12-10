import abc
import io
from typing import BinaryIO, Optional


class Strategy(abc.ABC):
    def __init__(
        self,
        *,
        target_contents: Optional[BinaryIO],
        template_contents: BinaryIO,
        template_commit_hash: str,
    ) -> None:
        self.target_contents = target_contents
        self.template_contents = template_contents
        self.template_commit_hash = template_commit_hash

    @abc.abstractmethod
    def apply(self) -> BinaryIO:
        pass


class Overwrite(Strategy):
    def apply(self) -> BinaryIO:
        return self.template_contents


class TemplateHash(Strategy):
    line_comment_start = "#"

    def apply(self) -> BinaryIO:
        hash_comment = (
            f"{self.line_comment_start} "
            f"https://github.com/rambler-digital-solutions/scaraplate template "
            f"commit hash: {self.template_commit_hash}\n"
        ).encode("ascii")
        if self.target_contents is not None:
            target_text = self.target_contents.read()
            if hash_comment in target_text:
                # Hash hasn't changed -- keep the target.
                self.target_contents.seek(0)
                return self.target_contents

        out_bytes = self.template_contents.read()
        out_bytes += b"\n" + hash_comment
        return io.BytesIO(out_bytes)


# XXX setup.cfg
# XXX .pylintrc
