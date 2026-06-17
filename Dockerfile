FROM public.ecr.aws/gravitational/teleport-distroless-debug:18.8.3 AS teleport

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=teleport /usr/local/bin/teleport /usr/local/bin/teleport
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

ENTRYPOINT ["sunpanel-teleport-bridge"]
CMD ["sync"]
