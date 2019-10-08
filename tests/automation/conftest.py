import http.server
import socketserver
import threading
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Callable, List, Optional

import pytest


def convert_git_repo_to_bare(call_git, *, cwd: Path) -> None:
    """Git bare repo is a git repo without a working copy. `git clone`
    can clone these repos my simply pointing at their location in the local
    filesystem.
    """
    # https://stackoverflow.com/a/3251126
    call_git("git config --bool core.bare true", cwd=cwd)


@pytest.fixture
def template_bare_git_repo(tempdir_path, init_git_and_commit, call_git):
    template_path = tempdir_path / "remote_template"

    cookiecutter_path = template_path / "{{cookiecutter.project_dest}}"
    cookiecutter_path.mkdir(parents=True)
    (cookiecutter_path / "sense_vars").write_text("{{ cookiecutter|jsonify }}\n")
    (cookiecutter_path / ".scaraplate.conf").write_text(
        """[cookiecutter_context]
{%- for key, value in cookiecutter.items()|sort %}
{{ key }} = {{ value }}
{%- endfor %}
"""
    )
    (template_path / "cookiecutter.json").write_text(
        '{"project_dest": "test", "key1": null, "key2": null}'
    )
    (template_path / "scaraplate.yaml").write_text(
        """
git_remote_type: scaraplate.gitremotes.GitLab
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping: {}
        """
    )
    init_git_and_commit(template_path, with_remote=False)
    call_git("git branch master2", cwd=template_path)

    convert_git_repo_to_bare(call_git, cwd=template_path)

    return template_path


@pytest.fixture
def project_bare_git_repo(tempdir_path, init_git_and_commit, call_git):
    target_project_path = tempdir_path / "remote_project"

    target_project_path.mkdir(parents=True)
    (target_project_path / "readme").write_text("hi")
    init_git_and_commit(target_project_path, with_remote=False)
    call_git("git branch master2", cwd=target_project_path)

    convert_git_repo_to_bare(call_git, cwd=target_project_path)

    return target_project_path


@pytest.fixture
def http_server():
    server_thread = HttpServerThread()
    server_thread.start()
    yield server_thread
    server_thread.stop()
    server_thread.join()


class HttpServerThread(threading.Thread):
    spinup_timeout = 10

    def __init__(self):
        self.server_host = "127.0.0.1"
        self.server_port = None  # randomly selected by OS

        self.http_server = None
        self._errors: List[Exception] = []
        self.request_handler: Optional[Callable[..., Any]] = None

        # Future is generic. Pylint is wrong.
        # https://github.com/python/typeshed/blob/6e4708ebf3a482aa8d524196712c37c9fd645953/stdlib/3/concurrent/futures/_base.pyi#L26  # noqa
        self.socket_created_future: Future[  # pylint: disable=unsubscriptable-object
            bool
        ] = Future()

        super().__init__()
        self.daemon = True

    def set_request_handler(
        self, request_handler: Callable[..., Any]
    ) -> Callable[..., Any]:
        assert self.request_handler is None
        self.request_handler = request_handler
        return request_handler

    def get_url(self):
        assert self.socket_created_future.result(self.spinup_timeout)
        return f"http://{self.server_host}:{self.server_port}"

    def run(self):
        assert (
            self.http_server is None
        ), "This class is not reentrable. Please create a new instance."

        thread = self

        class Server(http.server.BaseHTTPRequestHandler):
            def __request_handler(self, method):
                if thread.request_handler is None:  # pragma: no cover
                    self.send_error(500, "request_handler is None")
                else:
                    try:
                        # https://stackoverflow.com/a/20879937
                        body = self.rfile.read(
                            int(self.headers.get("content-length", 0))
                        )
                        # fmt: off
                        code, headers, body = (
                            thread.request_handler(  # pylint: disable=not-callable
                                method, self.path, headers=self.headers, body=body
                            )
                        )
                        # fmt: on
                        self.send_response(code)
                        for name, value in headers.items():
                            self.send_header(name, value)
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception as e:  # pragma: no cover
                        thread._errors.append(e)

            def do_HEAD(self):  # pragma: no cover
                self.__request_handler("HEAD")

            def do_GET(self):
                self.__request_handler("GET")

            def do_POST(self):  # pragma: no cover
                self.__request_handler("POST")

            def do_PATCH(self):  # pragma: no cover
                self.__request_handler("PATCH")

        # ThreadingTCPServer offloads connections to separate threads, so
        # the serve_forever loop doesn't block until connection is closed
        # (unlike TCPServer). This allows to shutdown the serve_forever loop
        # even if there's an open connection.
        try:
            # TODO: switch to http.server.ThreadingHTTPServer
            # when the py36 support would be dropped
            self.http_server = socketserver.ThreadingTCPServer(
                (self.server_host, 0), Server
            )

            # don't hang if there're some open connections
            self.http_server.daemon_threads = True  # type: ignore

            self.server_port = self.http_server.server_address[1]
        except Exception as e:  # pragma: no cover
            self.socket_created_future.set_exception(e)
            raise
        else:
            self.socket_created_future.set_result(True)

        self.http_server.serve_forever()

    def stop(self):
        assert self.http_server is not None
        self.http_server.shutdown()  # stop serve_forever()
        self.http_server.server_close()

        # assert not self._errors
        # ^^^ gives unreadable assertions in pytest
        # This is better:
        if self._errors:
            raise self._errors[0]
