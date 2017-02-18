FROM python:3.5

COPY requirements.txt /
RUN pip install -r requirements.txt
WORKDIR /app
COPY app /app

CMD ["python", "molt.py"]
