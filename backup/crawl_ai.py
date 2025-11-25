import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from langchain.tools import tool
from rapidfuzz import fuzz

async def fetch_page_markdown(url: str) -> dict:
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return {
                "status": "success",
                "content": result.markdown
            }
    except Exception as e:
        return {
            "status": "error",
            "content": f"Error crawling the page: {str(e)}"
        }


@tool
async def return_page_markdown(url: str) -> dict:
    """
    Crawls the given URL and returns markdown content.

    Args:
        url: The URL of the page to crawl.

    Returns JSON:
        {
            "status": "success" | "error",
            "content": "<markdown text or error>"
        }

    Use this to fetch webpage content in markdown format.
    """
    return await fetch_markdown(url)


async def fetch_page_links(url: str, js_code: str = None) -> dict:
    config = CrawlerRunConfig(
        js_code="""
            const links = [...document.querySelectorAll('a')]
                .map(a => a.href)
                .filter(h => h); 
            return links;
        """
    )
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, config=config)
            return {
                "status": "success",
                "content": result.links 
            }

    except Exception as e:
        return {
            "status": "error",
            "content": f"Error crawling the page: {str(e)}"
        }


from rapidfuzz import fuzz
import re


def tokenize_url(url: str):
    url = url.lower()
    tokens = re.split(r'[^a-z0-9äöå]+', url)
    return [t for t in tokens if t]


def is_relevant_url(url: str, keywords: list, threshold:int = 80):
    tokens = tokenize_url(url)

    for token in tokens:
        for kw in keywords:
            if fuzz.ratio(token, kw) >= threshold: 
                return True

    return False

async def filter_links(url):
    res = await fetch_page_links(url)

    internal_links = [item['href'] for item in res['content'].get('internal', [])]
    external_links = [item['href'] for item in res['content'].get('external', [])]

    all_links = list(set(internal_links + external_links))

    keywords = [
        "career", "careers", "job", "jobs", "openjobs", "openpositions", "apply",
        "recruit", "recruitment", "join", "hiring", "work", "vacancies",
        "tyopaikka", "tyopaikat", "avoimet", "rekry", "rekrytointi", "ura", "toihin",
        "hae", "harjoittelu", "trainee", "kesätyö"
    ]
    print(all_links)
    filtered_links = [link for link in all_links if is_relevant_url(link, keywords, threshold=60)]
    print(filtered_links)
    return filtered_links


async def main():
    res = await run_js_on_page("https://careers.tietoevry.com/")

    keywords = [
        "career", "careers", "job", "jobs", "openjobs", "openpositions", "apply",
        "recruit", "recruitment", "join", "hiring", "work", "vacancies",
        "tyopaikka", "tyopaikat", "avoimet", "rekry", "rekrytointi", "ura", "toihin",
        "hae", "harjoittelu", "trainee", "kesätyö"
    ]

    passing_links = [link for link in all_links if is_relevant_url(link, keywords, threshold=80)]


    print(passing_links)
    

if __name__ == "__main__":
    asyncio.run(main())