docker run -d --name cs146s-dev --gpus all \
  -p 8000:8000 \
  -p 8765:8765 \
  -v "$(pwd)":/workspace \
  -w /workspace \
  -e OLLAMA_HOST=http://172.29.167.17:11434 \
  continuumio/miniconda3:latest sleep infinity
