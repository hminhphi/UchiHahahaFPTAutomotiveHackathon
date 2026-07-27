FROM python:3.12-slim

# Cài đặt thư viện hệ thống cần thiết (cho OpenCV và các xử lý ảnh)
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

# Cài đặt uv
RUN pip install uv

WORKDIR /app

# Copy các file quản lý thư viện trước để tận dụng cache của Docker
COPY pyproject.toml uv.lock ./

# Cài đặt dependencies
RUN uv sync --no-dev

# Copy toàn bộ mã nguồn
COPY . .

# Chạy script agent kết nối KUKSA mặc định
CMD ["uv", "run", "python", "scripts/carsky_agent.py"]
