FROM python:3.11-slim
WORKDIR /app
COPY proxy.py app_2.html ./
EXPOSE 8765
CMD ["python3", "proxy.py"]
