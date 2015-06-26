.PHONY: all
all:
	@echo "Hello $(shell whoami), nothing to do by default."
	@echo "Try 'make help'."

# target: clean - Remove .pyc files.
.PHONY: clean
clean:
	find ./ -name '*.pyc' -delete

# target: help - Display callable targets.
.PHONY: help
help:
	@echo "Bag8 make targets and variables:"
	@echo
	@sed -n '/^# target:/{s/# target: / /;p}' $(lastword $(MAKEFILE_LIST))
	@echo

# target: install - Install bag8.
.PHONY: install
install:
	pip install -e .

# target: install-test - Install tests requirements.
.PHONY: install-test
install-test:
	pip install -r requirements.tests.txt

# target: test-flake8 - Run flake8 tests.
.PHONY: test-flake8
test-flake8:
	flake8 bag8

# target: test-debug - Run tests in fail fast and very verbose way.
.PHONY: test-debug
test-debug: clean test-flake8
	py.test -sx -vv

# target: test-xdist - Run parallels tests.
.PHONY: test-xdist
test-xdist: clean test-flake8
	py.test -n3 --boxed

# target: test - Run tests for several versions of python with tox.
.PHONY: test
test: clean test-flake8
	tox
