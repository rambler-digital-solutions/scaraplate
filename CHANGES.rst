CHANGES
=======

0.2
---
2019-10-22

New features:

* Add RenderedTemplateFileHash strategy (#7).
  Contributed by Jonathan Piron.
* Raise an error when the cookiecutter context file is not generated (#9)
* Add support for extra_context to cli (like in `cookiecutter` command) (#10)
* Add jinja2 support to strategies mapping (#13)
* Add automation via Python + built-in support for Git-based projects 
  and GitLab (#11)

Behaviour changes:

* Strategies: detect newline type from the target file and preserve it (#12)

Packaging changes:

* Add ``jinja2`` requirement (#13)
* Add ``setuptools`` requirement (for ``pkg_resources`` package) (#11)
* Add ``[gitlab]`` extras for installing ``python-gitlab`` (#11)
* Add support for Python 3.8


0.1
---
2019-07-27

Initial public release.
