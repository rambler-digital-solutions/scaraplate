Cookiecutter template
=====================

Scaraplate uses cookiecutter under the hood, so the scaraplate template
must be a :doc:`cookiecutter template <cookiecutter_rtd:overview>` with
the following properties:

- There must be a ``scaraplate.yaml`` config in the root of
  the template dir (near the ``cookiecutter.json``).
- The template dir must be a git repo.
- The cookiecutter's project dir must be called ``project_dest``,
  i.e. the template must reside in the ``{{cookiecutter.project_dest}}``
  directory.
- The template must contain a file which would render the current
  cookiecutter context. Scaraplate then reads that context to re-apply
  cookiecutter template on subsequent roll-ups.


Cookiecutter context types
--------------------------

.. automodule:: scaraplate.cookiecutter
   :members: __doc__


.. autoclass:: scaraplate.cookiecutter.CookieCutterContext
   :show-inheritance:
   :members:

   .. automethod:: __init__


.. autoclass:: scaraplate.cookiecutter.ScaraplateConf
   :show-inheritance:


.. autoclass:: scaraplate.cookiecutter.Setupcfg
   :show-inheritance:
