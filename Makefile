.PHONY: all
all:
	@echo "Hello $(shell whoami), nothing to do by default."
	@echo "Try 'make help'."

# target: clean - Remove .pyc files.
.PHONY: clean
clean:
	find ./ -name *.pyc -delete
	find ./ -name __pycache__ -type d | xargs rm -rf

# target: help - Display callable targets.
.PHONY: help
help:
	@echo "Bag8 make targets and variables:"
	@echo
	@sed -n '/^# target:/{s/# target: / /;p}' $(lastword $(MAKEFILE_LIST))
	@echo

# target: install - Install bag8.
.PHONY: install
install: clean
	pip install -U pip
	pip install -e .

# target: install-test - Install tests requirements.
.PHONY: install-test
install-test:
	pip install -e ".[test]"

# target: test - Run test in fail fast and very verbose way.
.PHONY: test
test:
	flake8 bag8
	py.test -sx -vv bag8
