import docker

client = docker.from_env()

logs = client.containers.run(
    image="sandbox:py",
    command="scip-python --help",
    auto_remove=False,
    stdout=True,
    stderr=True,
    name="python",
)


# In kết quả trả về từ container
print("\n--- OUTPUT TỪ CONTAINER ---")
print(logs.decode("utf-8"))
print("---------------------------\n")
print("Container đã chạy xong và tự động bị huỷ.")
