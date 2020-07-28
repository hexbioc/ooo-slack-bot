.ONESHELL:

.PHONY: init
init:
	@python3 -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt

format:
	@isort server/
	@black server/

start:
	@FLASK_ENV=development python -m server
