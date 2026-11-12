.PHONY: test-unit migration-fixtures verify-migration-fixtures test-helm-k3d \
	test-migrations-fresh test-migrations-existing \
	test-migrations-timescaledb-upgrade test-migrations-all

ANALYTICS_CLI ?= analytics-cli

test-unit:
	cd analytics-cli && pytest

migration-fixtures:
	./tests/migrations/scripts/generate-fixtures.sh

verify-migration-fixtures:
	./tests/migrations/scripts/verify-fixtures.sh

test-migrations-fresh:
	ANALYTICS_CLI=$(ANALYTICS_CLI) ./tests/migrations/scripts/test-fresh.sh

test-migrations-existing:
	ANALYTICS_CLI=$(ANALYTICS_CLI) ./tests/migrations/scripts/test-existing.sh 2.30.2

test-migrations-timescaledb-upgrade:
	ANALYTICS_CLI=$(ANALYTICS_CLI) ./tests/migrations/scripts/test-existing.sh 2.26.1

test-migrations-all: verify-migration-fixtures test-migrations-fresh \
	test-migrations-existing test-migrations-timescaledb-upgrade

test-helm-k3d:
	./tests/kubernetes/test-helm-lifecycle.sh
