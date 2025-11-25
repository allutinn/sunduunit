from .helpers import order_links_by_relevance

class CareerPipeline:

    def find_career_page(self, links: list[tuple[str, str]]) -> str:
        MAX_PROMPT_COUNT = 10
        prompt_count = 0

        # TO-DO: Order links by relevance
        ordered_links = order_links_by_relevance(links)
        found = None

        # TO-DO: Loop until the career page is found or the max prompt count is reached
        while found is None:
            # TO-DO: Send top X links to LLM to find the career page

            # TO-DO: Validate the proposal

            # TO-DO: If proposal is valid, return the link

            if prompt_count > MAX_PROMPT_COUNT:
                return None
        
        return found

    def run(self):
        pass

    def validate_proposal(self, proposal: str) -> bool:
        return True

    def get_next_link(self, proposal: str) -> str:
        return proposal

    def get_career_page(self, link: str) -> str:
        return link