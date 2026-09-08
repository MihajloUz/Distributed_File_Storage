FROM python:3.13
WORKDIR /app

COPY python_logic/requirements.txt ./
COPY python_logic ./

RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
