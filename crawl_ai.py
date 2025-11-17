import asyncio
from crawl4ai import AsyncWebCrawler
from langchain.tools import tool


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


async def main():
    result = await return_page_markdown.arun({"url": "https://almpartners.fi/"})
    print(result)

if __name__ == "__main__":
    asyncio.run(main())