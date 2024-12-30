FROM python:3.9-slim

COPY venv/ ./venv/

ENV PATH="/app/venv/bin:$PATH"
COPY . .

CMD ["python", "app.py"]