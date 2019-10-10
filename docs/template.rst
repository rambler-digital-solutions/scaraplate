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


.. _no_input_mode:

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


Template Maintenance
--------------------

Given that scaraplate provides ability to update the already created
projects from the updated templates, it's worth discussing the maintenance
of a scaraplate template.

Removing a template variable
++++++++++++++++++++++++++++

Template variables could be used as :ref:`feature flags <feature_flags>`
to gradually introduce some changes in the templates which some target
projects might not use (yet) by disabling the flag.

But once the migration is complete, you might want to remove the no longer
needed variable.

Fortunately this is very simple: just stop using it in the template and
remove it from ``cookiecutter.json``. On the next ``scaraplate rollup``
the removed variable will be automatically removed from
the :ref:`cookiecutter context file <cookiecutter_context_types>`.

Adding a new template variable
++++++++++++++++++++++++++++++

The process for adding a new variable is the same as for removing one:
just add it to the ``cookiecutter.json`` and you can start using it in
the template.

If the next ``scaraplate rollup`` is run with ``--no-input``, the new
variable will have the default value as specified in ``cookiecutter.json``.
If you need a different value, you have 2 options:

1. Run ``scraplate rollup`` without the ``--no-input`` flag so the value
   for the new variable could be asked interactively.
2. Manually add the value to
   the :ref:`cookiecutter context section <cookiecutter_context_types>`
   so the next ``rollup`` could pick it up.

Restructuring files
+++++++++++++++++++

Scaraplate strategies intentionally don't provide support for anything
more complex than a simple file-to-file change. It means that a scaraplate
template cannot:

1. Delete or move files in the target project;
2. Take multiple files and union them.

The reason is simple: such operations are always the one-time ones so it
is just easier to perform them manually once than to maintain that logic
in the template.


Patterns
--------

This section contains some patterns which might be helpful for
creating and maintaining a scaraplate template.

.. _feature_flags:

Feature flags
+++++++++++++

Let's say you have a template which you have applied to dozens of your
projects.

And now you want to start gradually introducing a new feature, let it
be a new linter.

You probably would not want to start using the new thing everywhere at once.
Instead, usually you start with one or two projects, gain experience
and then start rolling it up on the other projects.

For that you can use template variables as feature flags.
The :ref:`example template <scaraplate_example_template>` contains
a ``mypy_enabled`` variable which demonstrates this concept. Basically
it is a regular cookiecutter variable, which can take different values
in the target projects and thus affect the template by enabling or disabling
the new feature.

Include files
+++++++++++++

Consider ``Makefile``. On one hand, you would definitely want to have some
make targets to come from the template; on the other hand, you might need
to introduce custom make targets in some projects. Coming up with a scaraplate
strategy which could merge such a file would be quite difficult.

Fortunately, ``Makefile`` allows to include other files. So the solution
is quite trivial: have ``Makefile`` synced from the template (with
the :class:`scaraplate.strategies.Overwrite` strategy), and include
a ``Makefile.inc`` file from there which will not be overwritten by the template.
This concept is demonstrated in the :ref:`example template <scaraplate_example_template>`.

Manual merging
++++++++++++++

Sometimes you need to merge some files which might be modified in the target
projects and for which there's no suitable strategy yet. In this case
you can use :class:`scaraplate.strategies.TemplateHash` strategy as
a temporary solution: it would overwrite the file each time a new
git commit is added to the template, but keep the file unchanged since
the last rollup of the same template commit.

The :ref:`example template <scaraplate_example_template>` uses this
approach for ``setup.py``.

Create files conditionally
++++++++++++++++++++++++++

:doc:`Cookiecutter hooks <cookiecutter_rtd:advanced/hooks>` can be used
to post-process the generated :ref:`temporary project <how_it_works>`.
For example, you might want to skip some files from the template
depending on the variables.

The :ref:`example template <scaraplate_example_template>` contains
an example hook which deletes ``mypy.ini`` file when the ``mypy_enabled``
variable is not set to ``1``.
