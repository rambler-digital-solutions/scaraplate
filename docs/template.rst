Scaraplate template
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


``scaraplate rollup`` has a ``--no-input`` switch which doesn't ask for
cookiecutter context values. This can be used to automate rollups
when the cookiecutter context is already present in the target project
(i.e. ``scaraplate rollup`` has been applied before). But the first rollup
should be done without the ``--no-input`` option, so the cookiecutter
context values could be filled by hand interactively.

The arguments to the ``scaraplate rollup`` command must be local
directories (i.e. the template git repo must be cloned manually,
scaraplate doesn't support retrieving templates from git remote directly).


.. _cookiecutter_context_types:

Cookiecutter context types
--------------------------

.. automodule:: scaraplate.cookiecutter
   :members: __doc__


.. autoclass:: scaraplate.cookiecutter.CookieCutterContext
   :show-inheritance:
   :members:

   .. automethod:: __init__


Built-in cookiecutter context types
-----------------------------------

.. autoclass:: scaraplate.cookiecutter.ScaraplateConf
   :show-inheritance:


.. autoclass:: scaraplate.cookiecutter.SetupCfg
   :show-inheritance:
