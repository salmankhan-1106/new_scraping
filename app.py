import os
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

REGISTRATION = os.getenv("REGISTRATION", "FA23-BAI-038")
NEWS_SOURCE = os.getenv("NEWS_SOURCE", "https://en.neonews.pk/")

app = Flask(__name__)


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def _find_first_result(driver: webdriver.Chrome) -> str:
    selectors = [
        "h3 a",
        "h2 a",
        ".search-results a",
        ".td_module_wrap h3 a",
        "article h2 a",
        "article h3 a",
    ]
    for selector in selectors:
        links = driver.find_elements(By.CSS_SELECTOR, selector)
        for link in links:
            href = link.get_attribute("href") or ""
            if href.startswith(NEWS_SOURCE) and "?s=" not in href:
                return href
    return ""


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Try common article containers first, fallback to all paragraphs
    containers = soup.select("article") or soup.select(".td-post-content, .post-content")
    paragraphs = []
    if containers:
        for container in containers:
            paragraphs.extend(container.find_all("p"))
    else:
        paragraphs = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
    return re.sub(r"\s+", " ", text).strip()


def _summarize(text: str, max_sentences: int = 3) -> str:
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:max_sentences]).strip()
    return summary


def scrape_article(keyword: str) -> dict:
    driver = _build_driver()
    try:
        search_url = f"{NEWS_SOURCE}?s={quote_plus(keyword)}"
        driver.get(search_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        first_url = _find_first_result(driver)
        if not first_url:
            return {
                "registration": REGISTRATION,
                "newssource": NEWS_SOURCE,
                "keyword": keyword,
                "url": "",
                "summary": "No results found.",
            }

        driver.get(first_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        article_text = _extract_text(driver.page_source)
        summary = _summarize(article_text)

        return {
            "registration": REGISTRATION,
            "newssource": NEWS_SOURCE,
            "keyword": keyword,
            "url": first_url,
            "summary": summary or "Summary not available.",
        }
    finally:
        driver.quit()


@app.route("/get", methods=["GET"])
def get_news():
    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return jsonify({"error": "keyword query parameter is required"}), 400
    data = scrape_article(keyword)
    return jsonify(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
