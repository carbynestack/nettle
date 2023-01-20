#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

.PHONY: all
all: carbyne-stack-mpc-client mp-spdz-mpc-client

.PHONY: build
build: carbyne-stack-mpc-client mp-spdz-mpc-client
	pip install -r requirements.txt

.PHONY: carbyne-stack-mpc-client
carbyne-stack-mpc-client:
	docker build -t nettle/carbynestack-mpc-client -f build/carbyne-stack-mpc-client.Dockerfile build

.PHONY: mp-spdz-mpc-client
mp-spdz-mpc-client:
	docker build -t nettle/mp-spdz-mpc-client -f build/mp-spdz-mpc-client.Dockerfile build
