# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY external_service.py .

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variable
ENV NAME external_service

# Run external_service.py when the container launches
CMD ["python", "external_service.py"]
