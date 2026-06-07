# Currently 3.13 is pre-release
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src
COPY app.py .
COPY .envrc .

CMD ["bash", "-c", "source .envrc && python3 app.py"]

