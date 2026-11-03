SHELL := /bin/bash
FLAVOR ?= kde
FLAVORS := kde gnome xfce cinnamon

.PHONY: help check iso all verify install-test clean

help:
	@echo "DebLite targets:"
	@echo "  make check             run shellcheck on the build scripts"
	@echo "  make iso FLAVOR=kde    build one ISO (needs sudo)"
	@echo "  make all               build all four release ISOs (needs sudo)"
	@echo "  make verify FLAVOR=kde verify out/deblite-13-kde-amd64.iso"
	@echo "  make install-test FLAVOR=kde  install that ISO to a loop image (needs sudo)"
	@echo "  make clean             remove build/ and out/"

check:
	shellcheck scripts/*.sh

iso:
	sudo -E ./scripts/build-iso.sh $(FLAVOR)

all:
	@set -e; for flavor in $(FLAVORS); do \
		sudo -E ./scripts/build-iso.sh $$flavor --release; \
	done

verify:
	./scripts/verify-iso.sh out/deblite-13-$(FLAVOR)-amd64.iso
	./scripts/audit-bloat.sh out/deblite-13-$(FLAVOR)-amd64.iso

install-test:
	sudo ./scripts/test-install.sh out/deblite-13-$(FLAVOR)-amd64.iso

clean:
	rm -rf build out
