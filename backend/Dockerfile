FROM python:3.12-slim

WORKDIR /app

# Runtime libs opencv-python-headless still dlopen's even in headless builds,
# plus a C++ toolchain to build insightface's bundled Cython extension.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-cv.txt ./
RUN pip install --no-cache-dir -r requirements-cv.txt && \
    pip install --no-cache-dir "bcrypt==4.0.1" "email-validator"

COPY . .

EXPOSE 8200
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
