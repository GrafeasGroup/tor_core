.PHONY: clean all test

all: develop test clean
	@true

clean:
	@# echo "Removing \`*.pyc', \`*.pyo', and \`__pycache__/'"
	@find . -regex '.+/[^/]+\.py[co]$$' -delete
	@find . -regex '.+/__pycache__$$' -exec rm -rf {} \; -prune

test: clean
	@python3 setup.py test

install: clean
	@python3 -m pip install --process-dependency-links -e .

develop: clean
	@python3 -m pip install --process-dependency-links -e .[dev]
