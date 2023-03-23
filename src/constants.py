NGINX_CONFIG = """server {
    listen 80;
    server_name {{ id }}.smartpro.solutions;

    location / {
        proxy_pass http://localhost:{{ port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
}"""

DOCKERFILE = """
FROM python:3.7
ARG LOCAL_PATH
WORKDIR /app
COPY ${LOCAL_PATH}/requirements.txt /app
RUN pip install --upgrade pip \    
    pip install --no-cache-dir -r requirements.txt
COPY ${LOCAL_PATH} /app
CMD ["python", "main.py"]
"""

PYTHON_FILE="""from flask import Flask, jsonify, request
import socket

app = Flask(__name__)

@app.route('/')
def main(): 
    return jsonify({
        "message": "Hello World!",
        "hostname": socket.gethostname(),
        "ip": request.remote_addr
    })
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
        """