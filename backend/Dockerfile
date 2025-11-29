# Use official Python base image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Copy backend code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose backend port (change if your backend runs on a different port)
EXPOSE 8000

# Run your backend application
CMD ["python", "main.py"]
