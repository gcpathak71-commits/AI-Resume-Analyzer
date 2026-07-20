# Dockerfile for Render (Docker runtime)
#
# Notes on why this image is built the way it is:
#
# 1. Python 3.11-slim (not 3.13-slim): pip installs prebuilt "wheels" for
#    most scientific packages (numpy, scipy, spaCy's dependencies, etc.)
#    only for Python versions that have been out a while. On a brand-new
#    Python version, pip often has no choice but to compile packages from
#    source, which needs far more build disk space, RAM, and time - this
#    was the main cause of "out of space" failures on Render's free tier.
#    3.11 has broad prebuilt-wheel coverage, so installs stay small & fast.
#
# 2. No sentence-transformers / torch: the job-recommendation feature was
#    switched to a scikit-learn TF-IDF comparison (see app/recommender.py)
#    instead of sentence-transformer embeddings. torch alone is several
#    hundred MB, which routinely exceeded Render's free-tier disk/RAM
#    budget (512MB RAM). Removing it is the single biggest size win.
#
# 3. Listens on $PORT: Render injects a PORT environment variable at
#    runtime and routes traffic to whatever port your app binds - it is
#    NOT fixed like Hugging Face's 7860. The shell-form CMD below expands
#    $PORT at container start, falling back to 8000 for local `docker run`.

FROM python:3.11-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr,
# so `print()` statements show up immediately in Render's build/runtime logs.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy only the requirements file first so Docker can cache this layer -
# rebuilds are much faster when only app code changes, not dependencies.
# The two `find` commands below strip test/cache bloat that ships inside
# some wheels but is never used at runtime, shrinking the final image.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm \
    && find /usr/local/lib -type d -name "__pycache__" -prune -exec rm -rf {} + \
    && find /usr/local/lib -type d -name "tests" -prune -exec rm -rf {} +

# Now copy the rest of the backend application code.
COPY . .

# Render sets $PORT itself; 8000 below is only a fallback for local runs
# like `docker run -p 8000:8000 <image>`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
