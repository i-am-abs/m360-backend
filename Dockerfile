FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Kolkata
WORKDIR /opt/app
RUN apt-get update && apt-get install -y tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
COPY . .
RUN addgroup --system m360 && adduser --system --ingroup m360 m360 \
    && mkdir -p /opt/app/data /opt/app/logs \
    && chown -R m360:m360 /opt/app
USER m360
EXPOSE 8000
ENV SERVER_PORT=8000 \
    UVICORN_WORKERS=2 \
    FORWARDED_ALLOW_IPS="*"
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port \"${SERVER_PORT}\" --workers \"${UVICORN_WORKERS}\" --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS}\""]