.ONESHELL:
SHELL := /bin/zsh
SRC = $(wildcard ./*.ipynb)

all: lemonpie docs

lemonpie: $(SRC)
	nbdev_build_lib
	touch lemonpie

sync:
	nbdev_update_lib

docs_serve: docs
	cd docs && bundle exec jekyll serve

docs: $(SRC)
	nbdev_build_docs
	touch docs

test:
	nbdev_test_nbs

release: pypi
		fastrelease_conda_package --upload_user corazonlabs
		nbdev_bump_version

conda_release:
		fastrelease_conda_package --mambabuild --upload_user corazonlabs

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
