FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Cài đặt thư viện hệ thống cần thiết cho OpenCV
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

# Chỉ copy pyproject.toml trước để cài dependencies (không copy uv.lock để tránh ép tải bản CUDA)
COPY pyproject.toml ./

# Đổi URL tải PyTorch từ CUDA (cu130) sang bản CPU để tối ưu dung lượng (tiết kiệm ~4GB)
RUN sed -i 's/cu130/cpu/g' pyproject.toml && \
    uv sync --no-dev

# Copy toàn bộ mã nguồn (đã bỏ qua thư mục data nhờ .dockerignore)
COPY . .

# Chạy script agent kết nối KUKSA mặc định
CMD ["uv", "run", "python", "scripts/carsky_agent.py"]
