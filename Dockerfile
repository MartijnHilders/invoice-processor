FROM python:3.12-slim
WORKDIR /app

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# run uv to install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy only the necessary files to the production container
COPY src/ ./src/
COPY config/ ./config/
COPY app.py .

# expose default streamlit port, adress is also already defaulted to localhost
EXPOSE 8501
CMD ["uv", "run", "--no-sync", "streamlit", "run", "app.py"]



