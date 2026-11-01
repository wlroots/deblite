SHELL := /bin/bash
FLAVOR ?= kde
FLAVORS := kde gnome xfce cinnamon

.PHONY: help test lint deb iso all clean

help:
	@echo "DebLite targets:"
	@echo "  make test              run the pytest suite"
	@echo "  make lint              compile-check Python and run shellcheck"
	@echo "  make deb               build out/deblite-installer_<version>_amd64.deb"
	@echo "  make iso FLAVOR=kde    build one ISO (needs sudo)"
	@echo "  make all               build all four release ISOs (needs sudo)"
	@echo "  make clean             remove build/ and out/"

test:
	python3 -m pytest -q

lint:
	python3 -m compileall -q installer tests
	shellcheck scripts/*.sh bin/deblite-installer

deb:
	./scripts/build-installer-deb.sh

iso:
	sudo ./scripts/build-iso.sh $(FLAVOR)

all:
	@set -e; for flavor in $(FLAVORS); do \
		sudo ./scripts/build-iso.sh $$flavor --release; \
	done

clean:
	rm -rf build out
