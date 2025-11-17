import asyncio
import os
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator
import json

from crawl_ai import filter_links

# -------------------- STATE --------------------

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    pages: Annotated[dict[str, list[str]], operator.or_]  # now stores links, not markdown
    current_url: str | None
    next_step: str | None
    next_url: str | None
    careers_page: str | None
    analyze_page_system_prompt: str


# -------------------- LLM --------------------

model = ChatOpenAI(
    model="gpt-4.1-mini",
    base_url="https://munherkkuinstanssifoundry.openai.azure.com/openai/v1",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)


# -------------------- PROMPTS --------------------

CAREERS_PAGE_DEFINITION = """
A TRUE careers page is one where the job listing can be accessed directly OR visible without needing to navigate deeper.

You are NOT analyzing page text — you are analyzing available link structure.

Rules:

- If links contain words like: jobs, open positions, vacancies, join us, apply, recruitment portal → this is strong signal.
- If the page contains many links with career-related patterns (like an ATS domain), it likely leads to a hub.

FINAL careers page should be:

- The deepest, most complete job listing page.
- Not a marketing page, summary page, or redirect layer.
- Always check if there is a links like "domain.fi/careers/jobs" or "domain.fi/careers/all-jobs"  or "domain.fi/careers/browse" 

Do NOT choose single job posting links unless it is clear the site only has ONE job available.
"""

ANALYZE_PAGE_FOR_NEXT_STEP_PROMPT = f"""
You are analyzing a list of extracted hyperlinks from a website.

Your job is to determine whether this URL already appears to be the FINAL careers page, or whether another link should be followed.

{CAREERS_PAGE_DEFINITION}

---

Your response MUST be one of the following JSON formats:

1️⃣ If this URL **already appears to be the final careers/job listing page**:

{{
  "action": "CAREERS_PAGE_FOUND",
  "next_link": null
}}

---

2️⃣ If the current URL is NOT final, but there exists a link that is more promising for a final careers page:

{{
  "action": "NEXT_LINK_TO_CRAWL",
  "next_link": "<the single best next link>"
}}

---

3️⃣ If no promising career-related links exist:

{{
  "action": "NO_PROMISING_LINKS",
  "next_link": null
}}

---

Rules:

- Prefer large hub links over individual job postings.
- Prefer links containing keywords like: jobs, open positions, vacancies, careers.
- If the current page is the same page as the one you are trying to crawl, return done

Only output the JSON object — no additional text.
"""


# -------------------- NODES --------------------

async def start_node(state: MessagesState) -> dict:
    url = state["messages"][0]["content"].strip()
    return {
        "current_url": url,
        "messages": [{"role": "system", "content": f"Starting crawl at {url}"}]
    }


async def crawl_page_node(state: MessagesState) -> dict:
    try:
        url = state["current_url"]
        links= await filter_links(url)
        return {
            "pages": {url: links},
            "messages": [{"role": "system", "content": f"Fetched {len(links)} links at {url}"}]
        }
    except Exception as e:
        return {"messages": [{"role": "system", "content": f"Failed crawling {url}"}]}


async def analyze_page_for_next_step(state: MessagesState) -> dict:
    url = state["current_url"]
    links = state["pages"][url]

    response = await model.ainvoke(
        [
            {"role": "system", "content": state["analyze_page_system_prompt"]},
            {"role": "user", "content": "\n".join(links)}
        ]
    )

    return json.loads(response.content)


async def decide_next_step_node(state: MessagesState) -> dict:
    result = await analyze_page_for_next_step(state)

    action = result.get("action")
    next_url = result.get("next_link")

    # guard rail so it doesnt start looping the current url
    if next_url == state["current_url"]:
        action = "CAREERS_PAGE_FOUND"
        next_url = None

    return {
        "next_step": action,
        "current_url": next_url or state["current_url"],
        "messages": [{"role": "system", "content": f"Action: {action} - Next: {next_url}"}]
    }


def end_node(state: MessagesState) -> dict:
    if state.get("next_step") == "CAREERS_PAGE_FOUND":
        return {
            "messages": [{"role": "system", "content": f"Final careers page found: {state['current_url']}"}],
            "careers_page": state["current_url"]
        }

    return {
        "messages": [{"role": "system", "content": "No valid careers page found."}],
        "careers_page": None
    }


def next_step_router(state: MessagesState) -> str:
    match state.get("next_step"):
        case "NEXT_LINK_TO_CRAWL": return "crawl_page_node"
        case "CAREERS_PAGE_FOUND" | "NO_PROMISING_LINKS": return "end_node"
        case _: return "end_node"


# -------------------- BUILD AGENT --------------------

def build_agent():
    graph = StateGraph(MessagesState)

    graph.add_node("start_node", start_node)
    graph.add_node("crawl_page_node", crawl_page_node)
    graph.add_node("decide_next_step_node", decide_next_step_node)
    graph.add_node("end_node", end_node)

    graph.add_conditional_edges("decide_next_step_node", next_step_router)
    graph.add_edge(START, "start_node")
    graph.add_edge("start_node", "crawl_page_node")
    graph.add_edge("crawl_page_node", "decide_next_step_node")
    graph.add_edge("end_node", END)

    return graph.compile()


# -------------------- RUN --------------------

async def run_agent(agent, start_state):
    final_state = await agent.ainvoke(start_state)
    return final_state


if __name__ == "__main__":
    start_state = {
        "messages": [{"role": "user", "content": "https://www.luxidgroup.com/"}],
        "analyze_page_system_prompt": ANALYZE_PAGE_FOR_NEXT_STEP_PROMPT
    }

    agent = build_agent()
    result = asyncio.run(run_agent(agent, start_state))
    print(json.dumps(result, indent=2))