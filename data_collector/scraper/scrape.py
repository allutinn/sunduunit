from crawl4ai import AsyncWebCrawler

async def scrape_page_markdown(url: str) -> str:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success:
            #logging.error(f"Failed to scrape page {url}: {result.error_message}")
            print(f"Failed to scrape page {url}: {result.error_message}")
            return ""

        return result.markdown

async def scrape_links(url: str) -> list[tuple[str, str]]:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success:
            #logging.error(f"Failed to scrape links {url}: {result.error_message}")
            print(f"Failed to scrape links {url}: {result.error_message}")
            return []

        internal_links = result.links['internal']
        external_links = result.links['external']
        return [(link['href'], link['text']) for link in internal_links + external_links]

