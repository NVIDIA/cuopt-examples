FROM nvidia/cuda:12.6.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    jupyter \
    notebook \
    ipykernel \
    numpy>=1.20.0 \
    pandas>=1.3.0 \
    matplotlib>=3.4.0 \
    scipy>=1.7.0 \
    seaborn>=0.11.0 \
    plotly>=5.3.0 \
    nvidia-cuopt>=1.0.0 \
    cuopt-sh-client>=1.0.0 \
    folium>=0.12.0

# Create workspace directory
WORKDIR /workspace

# Copy the repository
# Directory structure follows [VERTICAL][SER/PY] pattern
# Example: INT_FAC_SER, LMD_PY, PDP_SER, etc.
COPY . /workspace/

# Expose Jupyter port
EXPOSE 8888

# Set the default command
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"] 