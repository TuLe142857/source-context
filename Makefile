.PHONY: help dev-up dev-down dev-logs dev-build dev-ps db-shell prod-up prod-down prod-logs prod-build prod-ps sync lint format typecheck test clean

# Variables
COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose-dev.yml
COMPOSE_PROD = docker compose -f docker-compose.yml

help: ## Hiển thị danh sách các lệnh hỗ trợ trong Makefile
	@echo "=========================================================================="
	@echo "                   Source Context - Makefile Commands                     "
	@echo "=========================================================================="
	@echo "Chế độ DEV (Development):"
	@echo "  make dev-up        - Khởi chạy tất cả container ở chế độ Development (Background)"
	@echo "  make dev-down      - Dừng và xóa tất cả container chế độ Development"
	@echo "  make dev-build     - Build lại các image và khởi chạy ở chế độ Development"
	@echo "  make dev-logs      - Xem log các container chế độ Development"
	@echo "  make dev-ps        - Kiểm tra trạng thái các container chế độ Development"
	@echo "  make db-shell      - Truy cập vào psql shell của Docker Postgres"
	@echo ""
	@echo "Chế độ PROD (Production):"
	@echo "  make prod-up       - Khởi chạy tất cả container ở chế độ Production (Background)"
	@echo "  make prod-down     - Dừng và xóa tất cả container chế độ Production"
	@echo "  make prod-build    - Build lại các image và khởi chạy ở chế độ Production"
	@echo "  make prod-logs     - Xem log các container chế độ Production"
	@echo "  make prod-ps       - Kiểm tra trạng thái các container chế độ Production"
	@echo ""
	@echo "Python & Code Quality:"
	@echo "  make sync          - Đồng bộ tất cả package bằng uv sync"
	@echo "  make format        - Định dạng code bằng ruff format"
	@echo "  make lint          - Kiểm tra linting bằng ruff check"
	@echo "  make typecheck     - Kiểm tra kiểu dữ liệu bằng mypy"
	@echo "  make test          - Chạy unit test với pytest"
	@echo "=========================================================================="

# ==============================================================================
# DEVELOPMENT COMMANDS
# ==============================================================================

dev-up: ## Khởi chạy môi trường Dev
	$(COMPOSE_DEV) up -d

dev-build: ## Build lại và khởi chạy môi trường Dev
	$(COMPOSE_DEV) up -d --build

dev-down: ## Dừng môi trường Dev
	$(COMPOSE_DEV) down

dev-logs: ## Xem logs môi trường Dev
	$(COMPOSE_DEV) logs -f

dev-ps: ## Xem trạng thái container Dev
	$(COMPOSE_DEV) ps

db-shell: ## Truy cập vào psql shell của Docker Postgres
	$(COMPOSE_DEV) exec postgres psql -U myuser -d mydb_dev

# ==============================================================================
# PRODUCTION COMMANDS
# ==============================================================================

prod-up: ## Khởi chạy môi trường Prod
	$(COMPOSE_PROD) up -d

prod-build: ## Build lại và khởi chạy môi trường Prod
	$(COMPOSE_PROD) up -d --build

prod-down: ## Dừng môi trường Prod
	$(COMPOSE_PROD) down

prod-logs: ## Xem logs môi trường Prod
	$(COMPOSE_PROD) logs -f

prod-ps: ## Xem trạng thái container Prod
	$(COMPOSE_PROD) ps

# ==============================================================================
# PYTHON & UTILITY COMMANDS
# ==============================================================================

sync: ## Đồng bộ thư viện uv
	uv sync --all-packages

format: ## Format Python code
	uv run ruff format .

lint: ## Check lint Python code
	uv run ruff check .

typecheck: ## Check mypy typing
	uv run mypy .

test: ## Chạy test suite
	uv run pytest

clean: ## Xóa cache và temp files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
