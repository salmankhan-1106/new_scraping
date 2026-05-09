FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        curl \
        gnupg \
        unzip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install matching ChromeDriver (Chrome for Testing)
RUN cat > /tmp/get_driver.py <<'EOF'
import json
import sys
from urllib.request import urlopen
chrome_version = sys.argv[1] if len(sys.argv) > 1 else ""
major = chrome_version.split('.')[0] if chrome_version else ""
data = json.load(urlopen("https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"))
entry = data["milestones"].get(major)
if not entry:
    raise SystemExit("No matching ChromeDriver for major version")
downloads = entry["downloads"]["chromedriver"]
url = next((d["url"] for d in downloads if d["platform"] == "linux64"), None)
if not url:
    raise SystemExit("No linux64 ChromeDriver found")
print(url)
EOF

RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    DRIVER_URL=$(python3 /tmp/get_driver.py "$CHROME_VERSION") && \
    curl -sSL -o /tmp/chromedriver.zip "$DRIVER_URL" && \
    unzip /tmp/chromedriver.zip -d /tmp/chromedriver && \
    mv /tmp/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver /tmp/chromedriver.zip /tmp/get_driver.py && \
    chmod +x /usr/local/bin/chromedriver

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY app.py /app/app.py

EXPOSE 7000

CMD ["python3", "app.py"]
