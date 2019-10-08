# PN - Project Name
PN := scaraplate
# PN - Project Version
PV := `python setup.py -q --version`

PYTHON := python3
SHELL  := /bin/sh

LINT_TARGET := setup.py src/ tests/
MYPY_TARGET := src/${PN} tests/

# Create the file below if you need to override the variables above
# or add additional make targets.
-include Makefile.inc


.PHONY: all
all: help


.PHONY: check
# target: check - Run all checks: linters and tests (with coverage)
check: lint test
	@${PYTHON} setup.py check


.PHONY: clean
# target: clean - Remove intermediate and generated files
clean:
	@${PYTHON} setup.py clean
	@find . -type f -name '*.py[co]' -delete
	@find . -type d -name '__pycache__' -delete
	@rm -rf {build,htmlcov,cover,coverage,dist,.coverage,.hypothesis}
	@rm -rf src/*.egg-info
	@rm -f VERSION


.PHONY: develop
# target: develop - Install package in editable mode with `develop` extras
develop:
	@${PYTHON} -m pip install --upgrade pip setuptools wheel
	@${PYTHON} -m pip install -e .[develop,gitlab]


.PHONY: dist
# target: dist - Build all artifacts
dist: dist-sdist dist-wheel


.PHONY: dist-sdist
# target: dist-sdist - Build sdist artifact
dist-sdist:
	@${PYTHON} setup.py sdist


.PHONY: dist-wheel
# target: dist-wheel - Build wheel artifact
dist-wheel:
	@${PYTHON} setup.py bdist_wheel


.PHONY: distcheck
# target: distcheck - Verify distributed artifacts
distcheck: distcheck-clean sdist
	@mkdir -p dist/$(PN)
	@tar -xf dist/$(PN)-$(PV).tar.gz -C dist/$(PN) --strip-components=1
	@$(MAKE) -C dist/$(PN) venv
	. dist/$(PN)/venv/bin/activate && $(MAKE) -C dist/$(PN) develop
	. dist/$(PN)/venv/bin/activate && $(MAKE) -C dist/$(PN) check
	@rm -rf dist/$(PN)


.PHONY: distcheck-clean
distcheck-clean:
	@rm -rf dist/$(PN)


.PHONY: format
# target: format - Format the code according to the coding styles
format: format-black format-isort


.PHONY: format-black
format-black:
	@black ${LINT_TARGET}


.PHONY: format-isort
format-isort:
	@isort -rc ${LINT_TARGET}


.PHONY: help
# target: help - Print this help
help:
	@egrep "^# target: " Makefile \
		| sed -e 's/^# target: //g' \
		| sort -h \
		| awk '{printf("    %-16s", $$1); $$1=$$2=""; print "-" $$0}'


.PHONY: install
# target: install - Install the project
install:
	@pip install .


.PHONY: lint
# target: lint - Check source code with linters
lint: lint-isort lint-black lint-flake8 lint-mypy lint-pylint


.PHONY: lint-black
lint-black:
	@${PYTHON} -m black --check --diff ${LINT_TARGET}


.PHONY: lint-flake8
lint-flake8:
	@${PYTHON} -m flake8 --statistics ${LINT_TARGET}


.PHONY: lint-isort
lint-isort:
	@${PYTHON} -m isort.main -df -c -rc ${LINT_TARGET}


.PHONY: lint-mypy
lint-mypy:
	@${PYTHON} -m mypy ${MYPY_TARGET}


.PHONY: lint-pylint
lint-pylint:
	@${PYTHON} -m pylint --rcfile=.pylintrc --errors-only ${LINT_TARGET}


.PHONY: purge
# target: purge - Remove all unversioned files and reset working copy
purge:
	@git reset --hard HEAD
	@git clean -xdff


.PHONY: report-coverage
# target: report-coverage - Print coverage report
report-coverage:
	@${PYTHON} -m coverage report


.PHONY: report-pylint
# target: report-pylint - Generate pylint report
report-pylint:
	@${PYTHON} -m pylint ${LINT_TARGET}


.PHONY: test
# target: test - Run tests with coverage
test:
	@${PYTHON} -m coverage run -m py.test
	@${PYTHON} -m coverage report


.PHONY: uninstall
# target: uninstall - Uninstall the project
uninstall:
	@pip uninstall $(PN)


# `venv` target is intentionally not PHONY.
# target: venv - Creates virtual environment
venv:
	@${PYTHON} -m venv venv


.PHONY: version
# target: version - Generate and print project version in PEP-440 format
version: VERSION
	@cat VERSION
VERSION:
	@echo ${PV} > $@
