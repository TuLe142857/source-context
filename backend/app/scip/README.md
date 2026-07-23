
scip.proto file is from: https://github.com/scip-code/scip

```shell
uv run python -m grpc_tools.protoc -I=. --python_out=. --pyi_out=. scip.proto
```