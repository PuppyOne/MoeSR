FROM python:3.13-slim
RUN mkdir -p /usr/app
WORKDIR /usr/app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt install cuda-toolkit
EXPOSE 9000
ENTRYPOINT ["python3", "-m", "fastapi", "run", "moe_sr.py", "--port", "9000"]
