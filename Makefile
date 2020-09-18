.PHONY: pypi tag mypy pytest test

pypi:
	poetry publish --build
	make tag

tag:
	git tag $$(poetry version --no-ansi | tr " " "\n" | tail -n 1)
	git push --tags

mypy:
	mypy --py2 --ignore-missing-imports popget

pytest:
	py.test -v -s --ipdb tests/

test:
	$(MAKE) mypy
	$(MAKE) pytest
