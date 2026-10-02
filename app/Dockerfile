# MEIDNet Studio on Hugging Face Spaces (Docker SDK, CPU).
# The bundle this file is copied into is produced by app/deploy_docker_space.py:
#   meidnet/  checkpoints/  data/perov5/train.csv  site/ (built docs)  requirements.txt
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
RUN useradd -m -u 1000 user
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .
USER user
ENV HOME=/home/user PYTHONPATH=/app
EXPOSE 7860

CMD ["python", "-m", "meidnet.studio.server", \
     "--host", "0.0.0.0", "--port", "7860", "--public", "--no-open", \
     "--run-root", "/home/user/runs", "--docs-dir", "/app/site", \
     "--model", "/app/checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"]
