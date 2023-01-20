# Nettle

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

Nettle is an integration layer between the [Flower] federated learning framework
and Carbyne Stack. Nettle allows for large-scale privacy-preserving federated
learning with MPC-based secure aggregation and protects against inference
attacks.

## Namesake

A _nettle_ is a chiefly coarse herb armed with stinging hairs. Carbyne Stack
Nettle is a fortified version of Flower that can resist certain kinds of
attacks.

## Development

### Generating the gRPC code

You can generate the GRPC-related code using

```shell
python3 -m grpc_tools.protoc -I protos --pyi_out=generated \ 
  --python_out=generated --grpc_python_out=generated \
  protos/model_training.proto
```

[flower]: https://flower.dev/
