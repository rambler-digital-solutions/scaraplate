CHANGES
=======

0.5
---
2023-07-23

* Fix windows path handling in rollup (#22).
  Contributed by john-zielke-snkeos.


0.4
---
2022-11-12

Packaging changes:

* Drop support for Python 3.6
* Add support for Python 3.9, 3.10, 3.11
* Add support for click>=8, jinja2 3, PyYAML>=6
* Add support for cookiecutter>=2.0.1 (see notes below)

Cookiecutter 2.0.1:

In 2.0.1 the `cookiecutter` jinja2 variable has been extended with a new
`_output_dir` key. In scaraplate this is some random dir in a temp space,
so having it in the template context is unwanted, because it would cause
the target project to be updated with the random tempdir on each rollup.

So in order to support cookiecutter>=2.0.1 you need to make a change in
your scaraplate template, where you write your cookiecutter context.
Suppose you have the following in your `.scaraplate.conf`:

    [cookiecutter_context]
    {%- for key, value in cookiecutter.items()|sort %}
    {{ key }} = {{ value }}
    {%- endfor %}

Then you need to add an exclusion for the `_output_dir` var, like this:

    [cookiecutter_context]
    {%- for key, value in cookiecutter.items()|sort %}
    {%- if key not in ('_output_dir',) %}
    {{ key }} = {{ value }}
    {%- endif %}
    {%- endfor %}


0.3
---
2020-05-11

Packaging changes:

* Add support for PyYAML 5
* Add support for marshmallow 3


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
