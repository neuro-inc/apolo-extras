COLOR ?= auto
PYTEST_FLAGS ?= -v
PYTEST_PARALLEL ?= auto # overwritten in CI
PYTHON ?= python
PACKAGE_NAME := apolo-extras
PACKAGE_VERSION = $(shell $(PYTHON) apolo_extras/version.py)

.PHONY: setup setup-ci setup-build
setup: setup-ci
	poetry run pre-commit install

setup-ci:
	poetry install --with dev,build
	poetry run python -m pip install --no-deps --no-build-isolation -e .

setup-build:
	poetry install --only main,build

.PHONY: build
build:
	poetry run python -m build --no-isolation

.PHONY: lint
lint: format
	poetry run mypy apolo_extras tests

.PHONY: format
format:
	poetry run pre-commit run --all-files --show-diff-on-failure

.PHONY: prepare-e2e-test
prepare-e2e-test:
	poetry run sh tests/e2e/data/prepare.sh

.PHONY: test_e2e
test_e2e:
	poetry run pytest -n $(PYTEST_PARALLEL) $(PYTEST_FLAGS) -m "(not serial) and (not smoke_only)" \
		--color=$(COLOR) tests/e2e
	poetry run pytest -n 0                  $(PYTEST_FLAGS) -m "serial and (not smoke_only)" \
		--color=$(COLOR) tests/e2e

.PHONY: test_smoke
test_smoke: test_unit test_e2e_smoke

.PHONY: test_e2e_smoke
test_e2e_smoke:
	poetry run pytest -n $(PYTEST_PARALLEL) \
		$(PYTEST_FLAGS) \
		-m "(not serial) and smoke" \
		--color=$(COLOR) \
		--runxfail \
		tests/e2e
	poetry run pytest -n 0 \
		$(PYTEST_FLAGS) \
		-m "serial and smoke" \
		--color=$(COLOR) \
		--runxfail \
		tests/e2e

.PHONY: test_data
test_data:
	poetry run pytest -n $(PYTEST_PARALLEL) \
		$(PYTEST_FLAGS) \
		-k "not serial and not smoke_only" \
		--color=$(COLOR) \
		tests/e2e/data
	poetry run pytest -n 0 \
		$(PYTEST_FLAGS) \
		-k "serial and not smoke_only" \
		--color=$(COLOR) \
		tests/e2e/data

.PHONY: test_image
test_image:
	poetry run pytest -n $(PYTEST_PARALLEL) \
		$(PYTEST_FLAGS) \
		-k "not serial and not smoke_only" \
		--color=$(COLOR) \
		tests/e2e/test_image.py
	poetry run pytest -n 0 \
		$(PYTEST_FLAGS) \
		-k "serial and not smoke_only" \
		--color=$(COLOR) \
		tests/e2e/test_image.py

.PHONY: test
test: test_unit test_e2e

.PHONY: test_unit
test_unit:
	poetry run pytest $(PYTEST_FLAGS) --color=$(COLOR) tests/unit

.PHONY: changelog-draft
changelog-draft:
	poetry run towncrier --draft --name $(PACKAGE_NAME) --version v$(PACKAGE_VERSION)

.PHONY: changelog
changelog:
	poetry run towncrier --name $(PACKAGE_NAME) --version v$(PACKAGE_VERSION)

.PHONY: check-changelog
check-changelog:
	grep -Fq "v$(PACKAGE_VERSION) (" CHANGELOG.md

.PHONY: docs
docs:
	poetry run python build-tools/cli-help-generator.py CLI.in.md docs/cli.md
