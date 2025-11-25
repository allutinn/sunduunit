from .definitions import CAREER_PAGE_KEYWORDS

def order_links_by_relevance(links: list[str]) -> list[str]:
    """
    Orders links by relevance to career page
    
    A link gets 'relevancy' score by the amount of CAREER_PAGE_KEYWORDS the url + text contains
    """

    return # sorted links by relevancy