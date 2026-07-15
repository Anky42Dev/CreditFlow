FROM python:3.12-slim
WORKDIR /app
COPY scoring_service/requirements.txt ./scoring_service/requirements.txt
RUN pip install --no-cache-dir -r scoring_service/requirements.txt
COPY scoring_service/ ./scoring_service/
EXPOSE 9000
CMD ["uvicorn", "scoring_service.main:app", "--host", "0.0.0.0", "--port", "9000"]
