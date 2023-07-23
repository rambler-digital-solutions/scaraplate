# Release process

## Prepare

1. Update cookiecutter version in `docs/conf.py`, ensure `make docs` produces
   docs with browsable cookiecutter links.
1. Add missing `.. versionadded`/`.. versionchanged` directives
   where appropriate.
1. Add a changelog entry to the CHANGES.rst file.
1. Push the changes, ensure that the CI build is green and all tests pass.

## Release

1. Upload a new pypi release:
   ```
   git tag -s 0.5
   make clean
   make dist
   git push origin 0.5
   twine upload -s dist/*
   ```
1. Create a new release for the pushed tag at
   https://github.com/rambler-digital-solutions/scaraplate/releases
1. Upload a GPG signature of the tarball to the just created GitHub release,
   see https://wiki.debian.org/Creating%20signed%20GitHub%20releases

## Check

1. Ensure that the uploaded version works in a clean environment
   (e.g. `docker run -it --rm python:3.7 bash`)
   and execute the quickstart scenario in the docs.
1. Ensure that RTD builds have passed and the `stable` version has updated:
   https://readthedocs.org/projects/scaraplate/builds/
1. Ensure that the CI build for the tag is green.
