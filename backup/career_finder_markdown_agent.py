import asyncio
import os
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator
import json

from crawl_ai import fetch_page_markdown


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    pages: Annotated[dict[str, str], operator.or_]
    current_url: str | None
    next_step: str | None
    next_url: str | None
    careers_page: str | None
    analyze_page_system_prompt: str # Caches system prompt for token efficiency
    

model = ChatOpenAI(
    model="gpt-4.1-mini",
    base_url="https://munherkkuinstanssifoundry.openai.azure.com/openai/v1",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

CAREERS_PAGE_DEFINITION = """

A TRUE careers page is the final page where job listings are fully displayed.
This means:

- The page contains open positions, AND
- There is no further "See all jobs", "View more", "Show all", or similar link leading to a more complete listing.

If a page contains job listings but ALSO provides a link suggesting there is a more complete or final list,
**you must NOT classify it as the careers page.**
Instead, extract and return the link to the full listing page.

Examples of links indicating the page is NOT final:
- "See all jobs"
- "All open positions"
- "Browse full job listings"
- "More jobs"
- "Visit recruitment portal"
- "View all openings"


A careers page can include filters and pagination controls if that page already represents the main job board
(i.e., it is the central canonical listing location, not a promotional or summary page).

Direct links to ATS (job portals) are valid if they lead to full listings, not single application pages.
"""



ANALYZE_PAGE_FOR_NEXT_STEP_PROMPT = f"""
You are analyzing crawled markdown content from a webpage.

Your job is to decide whether this page is the FINAL careers page,
or whether we still need to follow another link to reach the final career listing.

Use the following definition to determine correctness:
{CAREERS_PAGE_DEFINITION}

---

Your response MUST be valid JSON following EXACTLY ONE of these formats:

1) If this page IS the final careers page:

{{
  "action": "CAREERS_PAGE_FOUND",
  "next_link": null
}}

---

2) If this page is NOT final, but contains a link that appears to lead to the final job listing (such as: see-all-jobs links, ATS portal, pagination, job listing hub, etc.):

{{
  "action": "NEXT_LINK_TO_CRAWL",
  "next_link": "<the single most promising URL>"
}}

---

3) If there are no job-related indicators and no useful links:

{{
  "action": "NO_PROMISING_LINKS",
  "next_link": null
}}

---

Rules and constraints:

- Respond **ONLY with JSON** — NO explanations, text, or formatting outside JSON.
- If multiple job-relevant links exist, choose the most comprehensive, highest-level listing.
- Do NOT return links to single job postings (unless the site only has ONE job, and it is clear this is the only listing).
- If uncertain, default to returning a link (NEXT_LINK_TO_CRAWL) rather than prematurely marking as careers page.

Return only the JSON object and nothing else.
"""


async def start_node(state: MessagesState) -> dict:
    """Extract URL from user message and store in state."""
    url = state["messages"][0]["content"].strip()

    return {
        "current_url": url,
        "messages": [{"role": "system", "content": f"Starting crawl at {url}"}]
    }


async def crawl_page_node(state: MessagesState) -> dict:
    """Reads markdown of page asynchronously."""
    url = state["current_url"]

    response = await fetch_page_markdown(url)

    if response['status'] == 'success':  
        markdown = response['content']
        return {
            "pages": {url: markdown},
            "messages": [{"role": "system", "content": f"Fetched markdown for url {url}"}]
        }

async def analyze_page_for_next_step(markdown, state: MessagesState) -> dict:
    """Asks the LLM what to do next and returns parsed JSON."""
    response = await model.ainvoke(
        [
            {"role": "system", "content": state["analyze_page_system_prompt"]},
            {"role": "user", "content": markdown}
        ]
    )

    return json.loads(response.content.strip())

async def decide_next_step_node(state: MessagesState) -> dict:
    current_url = state['current_url']
    markdown = state['pages'][current_url]

    response = await analyze_page_for_next_step(markdown, state)

    next_step = response.get('action')
    next_url = response.get('next_link')

    return {
        "next_step": next_step,
        "current_url": next_url or state["current_url"],
        "messages": [{"role": "system", "content": f"Decided next step: {next_step} for url {current_url}. {'Next url: ' + next_url if next_url else ''}"}]
    }

def end_node(state: MessagesState) -> dict:
    last_step = state.get("next_step")
    if last_step == "CAREERS_PAGE_FOUND":
        return {
            "messages": [{"role": "system", "content": f"Succesfully returned careers page: {state['current_url']}"}],
            "careers_page": state['current_url']
        }
    else:
        return {
            "messages": [{"role": "system", "content": f"Failed to receive careers page"}],
        }


def next_step_router(state: MessagesState) -> str:
    step = state.get("next_step")

    if step == "NEXT_LINK_TO_CRAWL":
        return "crawl_page_node"

    if step == "CAREERS_PAGE_FOUND":
        return "end_node"

    if step == "NO_PROMISING_LINKS":
        return "end_node"

    else:
        return "end_node"

def build_agent():
    graph = StateGraph(MessagesState)

    graph.add_node("start_node", start_node)
    graph.add_node("crawl_page_node", crawl_page_node)
    graph.add_node("decide_next_step_node", decide_next_step_node)
    graph.add_node("end_node", end_node)

    graph.add_conditional_edges(
        "decide_next_step_node",
        next_step_router
    )

    graph.add_edge(START, "start_node")
    graph.add_edge("start_node", "crawl_page_node")
    graph.add_edge("crawl_page_node", "decide_next_step_node")
    graph.add_edge("end_node", END)


    return graph.compile()


async def run_agent(agent, start_state):
    final_state = await agent.ainvoke(start_state)

    # ---- PRINT CLEAN OUTPUT ----
    print("\n============================")
    print(" Agent Message Log")
    print("============================\n")

    for msg in final_state.get("messages", []):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        print(f"[{role.upper()}] {content}\n")

    # ---- SAVE RAW FINAL STATE ----
    os.makedirs("logs", exist_ok=True)
    output_path = "logs/final_state.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_state, f, indent=2, ensure_ascii=False)

    print("======================================")
    print(f"Final state saved to: {output_path}")
    print("======================================\n")

if __name__ == "__main__":
    start_state = {
        "messages": [{"role": "user", "content": "https://almpartners.fi"}],
        "analyze_page_system_prompt": ANALYZE_PAGE_FOR_NEXT_STEP_PROMPT
    }

    agent = build_agent()
    asyncio.run(run_agent(agent, start_state))
