# Nettle

## Model Owner

You can generate the GRPC-related code using

```shell
python3 -m grpc_tools.protoc -Iprotos --python_out=generated/ \
  --grpc_python_out=generated protos/model_training.proto 
```