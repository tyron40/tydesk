FROM python:3.12-slim
WORKDIR /app
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt && useradd -m -u 10001 tydesk && mkdir /data && chown tydesk:tydesk /data
COPY server.py extensions.py ./
COPY templates ./templates
ENV TYDESK_HOST=0.0.0.0 TYDESK_DATA=/data PORT=8787 PYTHONUNBUFFERED=1
USER tydesk
EXPOSE 8787
CMD ["python", "server.py"]
