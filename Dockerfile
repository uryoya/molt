FROM python:3.5

COPY app /app
WORKDIR /app
RUN pip install -r requirements.txt

CMD ["python", "molt.py"]
