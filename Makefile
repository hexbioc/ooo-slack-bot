.ONESHELL:

.PHONY: init
init:
	@python3 -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt

format:
	@isort -rc server/
	@black server/

lint:
	@flake8 server/

start:
	@FLASK_ENV=development python -m server
