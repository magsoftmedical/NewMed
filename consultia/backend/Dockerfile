FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# Convert UTF-16 requirements.txt to UTF-8 for pip compatibility
RUN python -c "open('req-utf8.txt','w').write(open('requirements.txt','r',encoding='utf-16').read())" \
    && pip install --no-cache-dir -r req-utf8.txt \
    && rm req-utf8.txt

COPY server.py constants.py __init__.py ./

EXPOSE 5000

CMD ["uvicorn", "server:app", "--host=0.0.0.0", "--port=5000"]
