FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required by OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force uninstall UI OpenCV to ensure headless is used and no conflicts occur
RUN pip uninstall -y opencv-contrib-python opencv-python || true

# Copy the rest of the application
COPY . .

# Run the FastAPI server using the Railway PORT environment variable
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
