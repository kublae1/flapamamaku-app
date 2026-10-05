FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

ARG FLAPAMAMAKU_BUILD_SHA=development
ENV FLAPAMAMAKU_DB=/data/flapamamaku.db
ENV FLAPAMAMAKU_BUILD_SHA=$FLAPAMAMAKU_BUILD_SHA
EXPOSE 8000 8091

CMD ["uvicorn", "app.runtime:app", "--host", "0.0.0.0", "--port", "8000"]
