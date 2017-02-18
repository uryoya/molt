FROM python:3.5

RUN pip install -r reuiqrements.txt
WORKDIR /app
COPY app /app

CMD ["python", "molt.py"]

