
scip.proto file is from: https://github.com/scip-code/scip
commit hash: e01e97efac2f6b8c266b4d04825f1f1eab7b8f6c

```shell
cd backend/app/scip
uv run python -m grpc_tools.protoc -I=. --python_out=. --pyi_out=. scip.proto
```