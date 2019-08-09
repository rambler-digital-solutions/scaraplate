Scaraplate Template
===================

Scaraplate uses cookiecutter under the hood, so the scaraplate template
is a :doc:`cookiecutter template <cookiecutter_rtd:overview>` with
the following properties:

- There must be a ``scaraplate.yaml`` config in the root of
  the template dir (near the ``cookiecutter.json``).
- The template dir must be a git repo (because some strategies might render
  URLs to the template project and HEAD commit, making it easy to find out
  what template was used to rollup, see :doc:`gitremotes`).
- The cookiecutter's project dir must be called ``project_dest``,
  i.e. the template must reside in the ``{{cookiecutter.project_dest}}``
  directory.
- The template must contain a file which renders the current
  cookiecutter context. Scaraplate then reads that context to re-apply
  cookiecutter template on subsequent rollups
  (see :ref:`cookiecutter_context_types`).

``scaraplate.yaml`` contains:

- strategies (see :doc:`strategies`),
- cookiecutter context type (see :ref:`cookiecutter_context_types`),
- template git remote (see :doc:`gitremotes`).

.. note::
    Neither ``scaraplate.yaml`` nor ``cookiecutter.json`` would get
    to the target project. These two files exist only in the template
    repo. The files that would get to the target project are located
    in the inner ``{{cookiecutter.project_dest}}`` directory of the template repo.


``scaraplate rollup`` has a ``--no-input`` switch which doesn't ask for
cookiecutter context values. This can be used to automate rollups
when the cookiecutter context is already present in the target project
(i.e. ``scaraplate rollup`` has been applied before). But the first rollup
should be done without the ``--no-input`` option, so the cookiecutter
context values could be filled by hand interactively.

The arguments to the ``scaraplate rollup`` command must be local
directories (i.e. the template git repo must be cloned manually,
scaraplate doesn't support retrieving templates from git remote directly).


.. _scaraplate_example_template:

Scaraplate Example Template
---------------------------

We maintain an example template for a new Python project here:
https://github.com/rambler-digital-solutions/scaraplate-example-template

You may use it as a starting point for creating your own scaraplate template.
Of course it doesn't have to be for a Python project: the cookiecutter
template might be for anything. A Python project is just an example.

Creating a new project from the template
++++++++++++++++++++++++++++++++++++++++

::

    $ git clone https://github.com/rambler-digital-solutions/scaraplate-example-template.git
    $ scaraplate rollup ./scaraplate-example-template ./myproject
    `myproject1/.scaraplate.conf` file doesn't exist, continuing with an empty context...
    `project_dest` must equal to "myproject"
    project_dest [myproject]:
    project_monorepo_name []:
    python_package [myproject]:
    metadata_name [myproject]:
    metadata_author: Kostya Esmukov
    metadata_author_email: kostya@esmukov.ru
    metadata_description: My example project
    metadata_long_description [file: README.md]:
    metadata_url [https://github.com/rambler-digital-solutions/myproject]:
    coverage_fail_under [100]: 90
    mypy_enabled [1]:
    Done!
    $ tree -a myproject
    myproject
    ├── .editorconfig
    ├── .gitignore
    ├── .scaraplate.conf
    ├── MANIFEST.in
    ├── Makefile
    ├── README.md
    ├── mypy.ini
    ├── setup.cfg
    ├── setup.py
    ├── src
    │   └── myproject
    │       └── __init__.py
    └── tests
        ├── __init__.py
        └── test_metadata.py

    3 directories, 12 files

The example template also contains a ``project_monorepo_name`` variable
which simplifies creating subprojects in monorepos (e.g. a single git
repository for multiple projects). In this case scaraplate should be
applied to the inner projects:

::

    $ scaraplate rollup ./scaraplate-example-template ./mymonorepo/innerproject
    `mymonorepo/innerproject/.scaraplate.conf` file doesn't exist, continuing with an empty context...
    `project_dest` must equal to "innerproject"
    project_dest [innerproject]:
    project_monorepo_name []: mymonorepo
    python_package [mymonorepo_innerproject]:
    metadata_name [mymonorepo-innerproject]:
    metadata_author: Kostya Esmukov
    metadata_author_email: kostya@esmukov.ru
    metadata_description: My example project in a monorepo
    metadata_long_description [file: README.md]:
    metadata_url [https://github.com/rambler-digital-solutions/mymonorepo]:
    coverage_fail_under [100]: 90
    mypy_enabled [1]:
    Done!
    $ tree -a mymonorepo
    mymonorepo
    └── innerproject
        ├── .editorconfig
        ├── .gitignore
        ├── .scaraplate.conf
        ├── MANIFEST.in
        ├── Makefile
        ├── README.md
        ├── mypy.ini
        ├── setup.cfg
        ├── setup.py
        ├── src
        │   └── mymonorepo_innerproject
        │       └── __init__.py
        └── tests
            ├── __init__.py
            └── test_metadata.py

    4 directories, 12 files

Updating a project from the template
++++++++++++++++++++++++++++++++++++

::

    $ scaraplate rollup ./scaraplate-example-template ./myproject --no-input
    Continuing with the following context from the `myproject/.scaraplate.conf` file:
    {'_template': 'scaraplate-example-template',
     'coverage_fail_under': '90',
     'metadata_author': 'Kostya Esmukov',
     'metadata_author_email': 'kostya@esmukov.ru',
     'metadata_description': 'My example project',
     'metadata_long_description': 'file: README.md',
     'metadata_name': 'myproject',
     'metadata_url': 'https://github.com/rambler-digital-solutions/myproject',
     'mypy_enabled': '1',
     'project_dest': 'myproject',
     'project_monorepo_name': '',
     'python_package': 'myproject'}
    Done!


.. _cookiecutter_context_types:

Cookiecutter Context Types
--------------------------

.. automodule:: scaraplate.cookiecutter
   :members: __doc__


.. autoclass:: scaraplate.cookiecutter.CookieCutterContext
   :show-inheritance:
   :members:

   .. automethod:: __init__


Built-in Cookiecutter Context Types
-----------------------------------

.. autoclass:: scaraplate.cookiecutter.ScaraplateConf
   :show-inheritance:


.. autoclass:: scaraplate.cookiecutter.SetupCfg
   :show-inheritance:

.. autoclass:: scaraplate.cookiecutter.YAMLConf
   :show-inheritance:
