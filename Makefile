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
	mypy --py2 --ignore-missing-imports popget

pytest:
	py.test -v -s tests/

pytest-pdb:
	py.test -v -s --ipdb tests/

test:
	$(MAKE) mypy
	$(MAKE) pytest

