FROM python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f AS build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
COPY requirements.txt /opt/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes --timeout 20 --retries 1 -r /opt/requirements.txt
COPY tools/minimal_runtime.py /opt/minimal_runtime.py
RUN python /opt/minimal_runtime.py
FROM scratch AS runtime
COPY --from=build /rootfs /
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/usr/local/bin LD_LIBRARY_PATH=/usr/local/lib SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
USER 10001:10001
WORKDIR /product
CMD ["python", "-m", "app.transparent.server"]
