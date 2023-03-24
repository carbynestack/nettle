# Nettle

[![stability-wip](https://img.shields.io/badge/stability-wip-lightgrey.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#work-in-progress)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

Nettle is an integration layer between the [Flower] federated learning framework
and Carbyne Stack. Nettle allows for large-scale privacy-preserving federated
learning with MPC-based secure aggregation. It currently protects against
reconstruction attacks. In the future, it will also prevent unauthorized model
extraction.

See [CSEP-0055: Privacy-Preserving Federated Learning][csep-055] for details.

## Namesake

A _nettle_ is a chiefly coarse herb armed with stinging hairs. Carbyne Stack
Nettle is a fortified version of Flower that can resist certain kinds of
attacks.

## Usage

### Setup

To set up a virtual environment and install the dependencies, invoke the
following commands from the root of the Nettle repository:

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running an Experiment

To run a Nettle Federated Learning experiment using CIFAR-10, you first have to
start a Nettle Orchestrator using

<!-- markdownlint-disable MD013 -->

```shell
cd orchestrator
PYTHONPATH=$(pwd)/.. PYTHONUNBUFFERED=1 PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 orchestrator.py
```

<!-- markdownlint-enable MD013 -->

After that, launch the CIFAR-10 model owner using

<!-- markdownlint-disable MD013 -->

```shell
cd examples/cifar_10
PYTHONPATH=$(pwd)/../.. PYTHONUNBUFFERED=1 PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 cifar_model_owner.py
```

<!-- markdownlint-enable MD013 -->

Any finally start two Nettle Clients by executing the following commands twice

<!-- markdownlint-disable MD013 -->

```shell
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
`requirements.in` file. _After an update_ the corresponding `requirements.txt`
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

Carbyne Stack _Nettle_ is open-sourced under the Apache License 2.0. See the
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
