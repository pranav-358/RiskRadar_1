FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV and EasyOCR
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories first
RUN mkdir -p app/static/uploads/temp app/static/uploads/documents instance training_data/models

# Set matplotlib backend to non-interactive
ENV MPLBACKEND=Agg

# Train ML models (with error handling)
RUN python train_models.py || echo "Model training will happen at runtime"

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Run the application
CMD ["python", "run.py"]
