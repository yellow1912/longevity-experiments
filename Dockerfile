FROM python:3.14-slim

# US locale for USD pricing
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    TZ=America/New_York \
    PYTHONUNBUFFERED=1

# System deps for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install browser deps and fetch camoufox (patched Firefox for StealthyFetcher)
RUN python -m playwright install-deps firefox \
    && apt-get update && apt-get install -y --no-install-recommends libnspr4 libnss3 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m camoufox fetch \
    && python -m patchright install chromium

# Copy scraper module
COPY amazon_scraper/ amazon_scraper/

ENTRYPOINT ["python", "-m", "amazon_scraper.run"]
