# Use the base image
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    bzip2 \
    ca-certificates \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install micromamba
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba -C /usr/local/bin/

# Set environment variable for micromamba
ENV MAMBA_ROOT_PREFIX=/opt/micromamba
ENV PATH=$MAMBA_ROOT_PREFIX/bin:$PATH

# Copy the env.yaml file
COPY env.yaml /tmp/env.yaml

# Use SHELL in JSON format to make sure commands are executed in the correct environment
SHELL ["/bin/bash", "-c"]

# Create the micromamba environment using your YAML file
RUN micromamba create -y -f /tmp/env.yaml && \
    micromamba clean --all --yes

# Initialize the shell for micromamba activation and add it to .bashrc
RUN micromamba shell init --shell bash --root-prefix=$MAMBA_ROOT_PREFIX && \
    echo 'eval "$(micromamba shell hook --shell=bash)"' >> ~/.bashrc && \
    echo "micromamba activate py310_calpha" >> ~/.bashrc

# Default command to keep the container running and allow interactive sessions
CMD ["/bin/bash"]
