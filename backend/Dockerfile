FROM python:3.11-slim

# System dependencies:
#   tesseract-ocr + tesseract-ocr-eng : Tesseract OCR engine + English language data
#   poppler-utils                      : pdf2image uses pdftoppm/pdfinfo from Poppler
#   libmagic1                          : python-magic MIME-type detection
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "bcrypt>=3.2.0,<4.0.0"

COPY . .

# Storage directories (also mounted as a volume in compose so data persists)
RUN mkdir -p /app/storage/documents /app/storage/images

EXPOSE 8000

# --reload enables hot-reload in dev; remove for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
