FROM nvidia/cuda:12.6.0-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Copy the repository
# Directory structure is organized based on specific use cases
COPY . /workspace/

# Install Python packages
RUN pip3 install --no-cache-dir --quiet -r /workspace/requirements.txt

# Expose Jupyter port
EXPOSE 8888

# Set the default command
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
