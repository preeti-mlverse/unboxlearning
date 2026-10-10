# UnboxEd API + worker image (build from the repo root: docker build -f apps/api/Dockerfile .)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /repo
COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt
COPY apps/api apps/api
COPY database database
COPY workers workers
ENV PYTHONPATH=/repo/apps/api:/repo
RUN useradd --create-home unboxed && mkdir -p /data/storage && chown unboxed /data/storage
USER unboxed
EXPOSE 8040
CMD ["sh", "-c", "python -m alembic -c database/alembic.ini upgrade head && uvicorn unboxed_api.main:app --host 0.0.0.0 --port 8040 --proxy-headers"]
