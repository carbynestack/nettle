# Nettle

[![stability-wip](https://img.shields.io/badge/stability-wip-lightgrey.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#work-in-progress)
[![codecov](https://codecov.io/gh/carbynestack/nettle/branch/master/graph/badge.svg?token=fSu1ncbt6H)](https://codecov.io/gh/carbynestack/nettle)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/52418a64dcd54f02b3f358576a14fb04)](https://app.codacy.com/gh/carbynestack/nettle/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Known Vulnerabilities](https://snyk.io/test/github/carbynestack/nettle/badge.svg)](https://snyk.io/test/github/carbynestack/nettle)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

Nettle is an integration layer between the [Flower] federated learning framework
and Carbyne Stack. Nettle allows for large-scale privacy-preserving federated
learning with MPC-based secure aggregation. It currently protects against
reconstruction attacks. In the future, it will also prevent unauthorized model
extraction.

See [CSEP-0055: Privacy-Preserving Federated Learning][csep-055] for details.
Please note that Nettle currently implements only a subset of the system
proposed in CSEP-0055. In particular, the model plane protection mechanisms
based on Confidential Computing are still under active development.

> **DISCLAIMER**: Nettle is work-in-progress *alpha* software. The software is
> not ready for production use. It has neither been developed nor tested for a
> specific use case.

## Namesake

A **nettle** is a chiefly coarse herb armed with stinging hairs. Carbyne Stack
Nettle is a fortified version of Flower that can resist certain kinds of
attacks.

## Usage

### Setup

To set up a virtual environment and install the dependencies, invoke the
following commands from the root of the Nettle repository:

```shell
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pip-tools
pip-sync
```

To install dependencies and to build the Docker images required for running
Nettle in [MP-SPDZ](https://github.com/data61/MP-SPDZ)-based emulation mode,
invoke

```shell
make -j
```

### Running an Experiment

> **NOTE**: Remember that you have to activate the virtual environment in each
> shell launched subsequently.

To run a Nettle Federated Learning experiment using CIFAR-10 with secure
aggregation performed locally using a Docker-hosted 2-party MP-SPDZ backend, you
first have to start a Nettle Orchestrator using

<!-- markdownlint-disable MD013 -->

```shell
source .venv/bin/activate
cd orchestrator
PYTHONPATH=$(pwd)/.. PYTHONUNBUFFERED=1 PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 orchestrator.py
```

<!-- markdownlint-enable MD013 -->

After that, launch the CIFAR-10 model owner using

<!-- markdownlint-disable MD013 -->

```shell
source .venv/bin/activate
cd examples/cifar_10
PYTHONPATH=$(pwd)/../.. PYTHONUNBUFFERED=1 PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 cifar_model_owner.py
```

<!-- markdownlint-enable MD013 -->

Any finally start two Nettle Clients by executing the following commands twice

<!-- markdownlint-disable MD013 -->

```shell
source .venv/bin/activate
cd examples/cifar_10
PYTHONPATH=$(pwd)/../.. PYTHONUNBUFFERED=1 PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 cifar_client.py
```

<!-- markdownlint-enable MD013 -->

## Development

### Dependency Management

> **IMPORTANT**: Please make sure that the virtual environment is activated. See
> the [setup](#setup) section for details.

Dependencies are managed using
[pip-tools](https://github.com/jazzband/pip-tools). They are declared in the
`requirements.in` file. **After an update** the corresponding `requirements.txt`
file can be generated using

```shell
pip-compile
```

Syncing installed packages in the virtual environment is done using

```shell
pip-sync
```

### Generating the gRPC code

You can generate the GRPC-related code using

```shell
python3 -m grpc_tools.protoc -I protos --pyi_out=generated \
  --python_out=generated --grpc_python_out=generated \
  protos/model_training.proto
```

## License

Carbyne Stack **Nettle** is open-sourced under the Apache License 2.0. See the
[LICENSE](LICENSE) file for details.

### 3rd Party Licenses

For information on how license obligations for 3rd-party OSS dependencies are
fulfilled see the [README](https://github.com/carbynestack/carbynestack) file of
the Carbyne Stack repository.

## Contributing

Please see the Carbyne Stack
[Contributor's Guide](https://github.com/carbynestack/carbynestack/blob/master/CONTRIBUTING.md)

[csep-055]: https://github.com/carbynestack/carbynestack/blob/master/enhancements/0055-federated-learning.md
[flower]: https://flower.dev/
