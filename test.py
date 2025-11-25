from data_collector.scraper.scrape import scrape_page_markdown, scrape_links
import asyncio

res = asyncio.run(scrape_links("https://gofore.com/en/invest/governance/board-of-directors/"))
print(res)

#res = asyncio.run(scrape_page_markdown("https://duunitori.fi/tyopaikat"))
#print(res)

#with open("duunitori_tyopaikat.txt", "w", encoding="utf-8") as f:
#    f.write(res)