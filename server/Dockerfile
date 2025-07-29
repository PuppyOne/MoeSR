FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04
RUN apt update
RUN apt install -y python3 python3-pip
RUN mkdir -p /usr/app
WORKDIR /usr/app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 9000
ENTRYPOINT ["python3", "-m", "fastapi", "run", "app.py", "--port", "9000"]
