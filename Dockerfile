FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HOME=/home/app
RUN useradd --create-home --uid 1000 app
WORKDIR /home/app/application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
USER app
EXPOSE 7860
HEALTHCHECK --interval=30s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/_stcore/health')"
CMD ["python","-m","streamlit","run","app.py","--server.address=0.0.0.0","--server.port=7860","--server.headless=true"]
