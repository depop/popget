.PHONY: pypi tag mypy pytest pytest-pdb test

pypi:
	rm -f dist/*
	python setup.py sdist
	twine upload --config-file=.pypirc dist/*
	make tag

tag:
	git tag $$(python -c "from popget.__about__ import __version__; print(__version__)")
	git push --tags

mypy:
	mypy --ignore-missing-imports popget

pytest:
	py.test -v -s tests/

test:
	$(MAKE) mypy
	$(MAKE) pytest

