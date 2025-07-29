FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04
RUN apt update
RUN apt install -y python3 python3-pip
RUN apt install -y libcudnn9-cuda-12 libcudnn9-dev-cuda-12
RUN mkdir -p /usr/app
WORKDIR /usr/app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 9000
ENTRYPOINT ["python3", "-m", "fastapi", "run", "app.py", "--port", "9000"]
