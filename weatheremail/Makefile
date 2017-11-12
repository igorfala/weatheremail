HOST = 0.0.0.0
PORT = 8081
NEWSLETTERS = WD
API_LIMIT = 10
VERBOSITY = 1

SHELL = /usr/bin/env bash
TOPDIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))
REQUIREMENTS := $(wildcard requirements*.txt)
FLAKE_TARGETS := $(shell find $(TOPDIR) -type f -not -path '$(TOPDIR)/*/migrations*' -name '*.py')

.PHONY: requirements $(REQUIREMENTS) flake $(FLAKE_TARGETS) test

all: requirements

requirements: $(REQUIREMENTS)
$(REQUIREMENTS):
	@pip install -r $@

flake:
	flake8 --filename='*' $(FLAKE_TARGETS)

test: flake
	python $(TOPDIR)/manage.py test

run:
	python $(TOPDIR)/manage.py runserver $(HOST):$(PORT)

populate_cities:
	python $(TOPDIR)/manage.py populate_cities --verbosity $(VERBOSITY)

send_emails:
	python $(TOPDIR)/manage.py send_emails --newsletter $(NEWSLETTERS) --api-limit $(API_LIMIT) --verbosity $(VERBOSITY)
