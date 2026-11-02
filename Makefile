SHELL := /bin/bash
FLAVOR ?= kde
FLAVORS := kde gnome xfce cinnamon

.PHONY: help test lint deb iso all verify install-test clean

help:
	@echo "DebLite targets:"
	@echo "  make test              run the pytest suite"
	@echo "  make lint              compile-check Python and run shellcheck"
	@echo "  make deb               build out/deblite-installer_<version>_amd64.deb"
	@echo "  make iso FLAVOR=kde    build one ISO (needs sudo)"
	@echo "  make all               build all four release ISOs (needs sudo)"
	@echo "  make verify FLAVOR=kde verify out/deblite-13-kde-amd64.iso"
	@echo "  make install-test FLAVOR=kde  install that ISO to a loop image (needs sudo)"
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

verify:
	./scripts/verify-iso.sh out/deblite-13-$(FLAVOR)-amd64.iso
	./scripts/audit-bloat.sh out/deblite-13-$(FLAVOR)-amd64.iso

install-test:
	sudo ./scripts/test-install.sh out/deblite-13-$(FLAVOR)-amd64.iso

clean:
	rm -rf build out
