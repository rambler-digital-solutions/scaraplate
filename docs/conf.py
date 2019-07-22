# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import subprocess


# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------


def get_metadata_value(property_name):
    # Requires python >=3.5

    setup_py_dir = os.path.join(os.path.dirname(__file__), "..")
    setup_py_file = os.path.join(setup_py_dir, "setup.py")

    out = subprocess.run(
        ["python", setup_py_file, "-q", "--%s" % property_name],
        stdout=subprocess.PIPE,
        cwd=setup_py_dir,
        check=True,
    )
    property_value = out.stdout.decode().strip()
    return property_value


project = get_metadata_value("name")
author = get_metadata_value("author")

_copyright_year = 2019
copyright = "%s, %s" % (_copyright_year, author)

# The full version, including alpha/beta/rc tags
release = get_metadata_value("version")
# The short X.Y version
version = release.rsplit(".", 1)[0]  # `1.0.16+g40b2401` -> `1.0`

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Extension configuration -------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/", None),
}
