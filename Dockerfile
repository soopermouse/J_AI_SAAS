FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY j_platform ./j_platform
RUN pip install --no-cache-dir .
EXPOSE 8787
CMD ["j-platform"]
