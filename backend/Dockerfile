FROM python:3.11-slim 

WORKDIR /app 

# Dependências nativas obrigatórias para bcrypt/passlib 
RUN apt-get update && apt-get install -y \ 
    build-essential \ 
    libffi-dev \ 
    python3-dev \ 
    && apt-get clean 

COPY requirements.txt . 

RUN pip install --no-cache-dir -r requirements.txt 

COPY . . 

ENV PYTHONPATH=/app 

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]