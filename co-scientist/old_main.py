from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
from serpapi import GoogleSearch
import os
from functools import partial

# Load LLM inference endpoints from an env variable or a file
# See https://docs.ag2.ai/docs/FAQ#set-your-api-endpoints
# and OAI_CONFIG_LIST_sample

from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Review:
    review_summary: str = ""

    quick_review: str = "" # no web search, quick go through
    full_review: str = ""
    deep_verify_review: str = ""
    observe_review: str = ""
    simulation_review: str = ""


@dataclass
class Hypothesis:
    hid: str = "" # unique id
    rating: float =  1200.0 # ELO rating

    source_hypothesis: str = "" # A short version of the hypothesis    
    related_articles: List[Dict] = field(default_factory=list) # {"name": "article_name", "review": "literature_review", "link": "article_link"}

    detailed_hypothesis: str = "" # A detailed version of the hypothesis # after literature review

    debate_logs : List[str] = field(default_factory=list) # logs of the debate
    finalized_hypothesis: str = "" # after simulated scientific debate

    review: Review = Review()


context_variables = {
    "goal": "", # by the user at the beginning
    "notes": "", # from the user later giving feedback
    "configuration": { # parsed from the user's input by LLM
        "preferences": "",
        "idea_attributes": "",
        # "constraints": "",
    },

    "instructions": "", # from meta review agent? 

    # list of hypothesis
    "hypotheses": [], # List[Hypothesis]

    # ranking
    "pairwise_comparisons": [], #  List[Dict] {"hypothesis1": "hypothesis1_id", "hypothesis2": "hypothesis2_id", "winner": "hypothesis1_id"}

}

class GenerationAgent:
    def __init__(self):
        pass

    def web_search(self, query: str) -> str:
        # Get SERP API key from environment variables
        serp_api_key = os.getenv("SERP_API_KEY")
        if not serp_api_key:
            raise ValueError("SERP_API_KEY is not set in the environment variables")
        
        params = {
            "api_key": serp_api_key,
            "engine": "google",
            "q": query,
            "location": "United States",
            "google_domain": "google.com",
            "gl": "us",
            "hl": "en"
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "organic_results" not in results:
            return f"'organic_results' key not found in results: {results}. Use a less restrictive query."
        if not results['organic_results']:
            return f"No search results found for query: {query}. Try a more general query."
        
        web_snippets: List[str] = []
        
        for idx, page in enumerate(results["organic_results"], start=1):
            parts = [f"{idx}. [{page.get('title', 'No Title')}]({page.get('link', '')})"]
            
            if "source" in page:
                parts.append(f"Source: {page['source']}")
            
            if "date" in page:
                parts.append(f"Date published: {page['date']}")
            
            if "snippet" in page:
                parts.append(f"Snippet: {page['snippet']}")
            
            # Add sitelinks if available
            if "sitelinks" in page and "inline" in page["sitelinks"]:
                inline_links = page["sitelinks"]["inline"]
                sitelinks_str = "Sitelinks: " + ", ".join(
                    [f"[{link.get('title', '')}]({link.get('link', '')})" for link in inline_links]
                )
                parts.append(sitelinks_str)
            
            # Add structured about_this_result if available
            if "about_this_result" in page:
                about = page["about_this_result"]
                about_parts = []
                if "source" in about and "description" in about["source"]:
                    about_parts.append("Source: " + about["source"]["description"])
                if "keywords" in about:
                    about_parts.append("Keywords: " + ", ".join(about["keywords"]))
                if about_parts:
                    # Layer the about_this_result information with an indent
                    about_str = "About this result:\n\t" + "\n\t".join(about_parts)
                    parts.append(about_str)
            
            web_snippets.append("\n".join(parts))
        
        result_str = f"Google search results for '{query}' found {len(web_snippets)} results:\n\n" + "\n\n".join(web_snippets)
        return result_str

    def hypothesize(self, context_variables, hypothesis: Hypothesis):
        return hypothesis

    def multi_agent_debate(self, context_variables, hypothesis: Hypothesis):
        return hypothesis



class RankingAgent:
    def __init__(self):
        pass

    def compare_during_touranment(self, context_variables):
        pass

    def compare_during_debate(self, context_variables):
        pass

    def rank(self, context_variables):
        # determine whether the match require a debat or a quick comparison

        self.compare_during_touranment(context_variables)
        self.compare_during_debate(context_variables)
        return context_variables
    
    def prepare_tournament_match(self, context_variables):
        # 1. select the first hypothesis that is newer and top-ranking hypotheses

        # 2. select second hypothesis based on proximity ranking
        # not previously compared ones
        pass
        
        

# reflection.quick_review: no web search, quick go through

# reflection.full_review: with web search

# reflection.deep_verify_review: decompose into sub assumptions and verify

# reflection.observe_review:
# article
# hypothesis
# reflection.simulation_review: simulating the mechanism of action or the proposed experiment

class ReflectionAgent:
    def __init__(self):
        pass

    def quick_review(self, hypothesis: Hypothesis):
        pass

    def full_review(self, hypothesis: Hypothesis):
        # need to do web search
        pass

    def deep_verify_review(self, hypothesis: Hypothesis):
        pass

    def observe_review(self, hypothesis: Hypothesis):
        pass

    def simulation_review(self, hypothesis: Hypothesis):
        pass

    def get_review_overview(self, hypothesis: Hypothesis):
        pass


class EvolutionAgent:
    def __init__(self):
        pass

    def refine_hypothesis(self, hypothesis: Hypothesis):
        pass

    def mutate_hypothesis(self, context_variables):
        new_hypothesis = Hypothesis()
        return new_hypothesis
    

class MetaReviewAgent:
    def __init__(self):
        pass

    def review(self, context_variables):
        # update constraints ?
        pass


class Supervisor:
    def __init__(self):
        pass

    def supervise(self, context_variables):
        pass


def add_new_hypothesis(context_variables, hypothesis: Hypothesis):
    context_variables["hypotheses"].append(hypothesis)
    # get proximity agent
    return context_variables

def run_co_scientist(
    generation_agent: GenerationAgent,
    reflection_agent: ReflectionAgent,
    ranking_agent: RankingAgent,
    evolution_agent: EvolutionAgent,
        
):
    goal = input("What is your goal? ")
    context_variables["goal"] = goal
    working_hypothesis = Hypothesis()

    # fill one hypothesis
    working_hypothesis = generation_agent.web_search(context_variables=context_variables, hypothesis=working_hypothesis)
    working_hypothesis = generation_agent.hypothesize(context_variables=context_variables, hypothesis=working_hypothesis)
    working_hypothesis = generation_agent.multi_agent_debate(context_variables=context_variables, hypothesis=working_hypothesis)

    # get all reviews (or could selectively get reviews)
    working_hypothesis = reflection_agent.quick_review(working_hypothesis)
    working_hypothesis = reflection_agent.full_review(working_hypothesis)
    working_hypothesis = reflection_agent.deep_verify_review(working_hypothesis)
    working_hypothesis = reflection_agent.observe_review(working_hypothesis)
    working_hypothesis = reflection_agent.simulation_review(working_hypothesis)
    working_hypothesis = reflection_agent.get_review_overview(working_hypothesis)

    context_variables.append(working_hypothesis)

    # ranking
    context_variables = ranking_agent.rank(context_variables)



import asyncio
import time
import json
from dataclasses import dataclass
from typing import Callable, Awaitable, Any

# Global log structures.
task_history = []  # List of dicts with task details.
running_workers = {}  # Mapping of worker_id to current task info.
log_lock = asyncio.Lock()  # To protect concurrent log updates.

@dataclass
class WorkTask:
    name: str
    hid: str
    # A callable that returns an awaitable (the actual work to be done)
    coro: Callable[[], Awaitable[Any]]

# The worker function: a persistent loop that continuously processes tasks from the queue.
async def worker(queue: asyncio.Queue, worker_id: int):
    while True:
        task: WorkTask = await queue.get()
        start_time = time.time()
        # Record that this worker has started a task.
        async with log_lock:
            running_workers[worker_id] = {"task_name": task.name, "start_time": start_time}
        print(f"Worker {worker_id}: Starting task {task.name} at {start_time}")

        try:
            await task.coro()
        except Exception as e:
            print(f"Worker {worker_id}: Task {task.name} failed with error: {e}")
        finally:
            complete_time = time.time()
            # Update logs: remove from running_workers and add to task_history.
            async with log_lock:
                running_workers.pop(worker_id, None)
                task_history.append({
                    "task_name": task.name,
                    "worker_id": worker_id,
                    "start_time": start_time,
                    "complete_time": complete_time,
                })
            queue.task_done()
        print(f"Worker {worker_id}: Finished task {task.name} at {complete_time}")

# 1. the user gives input and we parse it -> update the context variables
# 2. we run generation.hypothesize to get a hypothesis with web search. it takes in the (goal, configuration) and add a new hypothesis. We can run 3 hypothesis generation in parallel.
# 3. three hypotheses are put into the list. Now when calling review, we need to specify which hypothesis to review, and the lock needs to be acquired.
# 4. at the completion, we now use the ranking agent to compare the hypotheses and assign elo ratings to them.

# after the above is completed, the initial phase is completed.
# we need logging: what hypothesis with id is generated, and what is the reviewed time for it, etc. when are two hypotheses compared, etc.

async def main():
    # Create the asynchronous work queue.
    work_queue = asyncio.Queue()

    # === Initialization Phase ===
    # Predefined sequence of tasks for initialization.
    init_tasks = [
        WorkTask("Init Task 1", lambda: asyncio.sleep(1)),
        WorkTask("Init Task 2", lambda: asyncio.sleep(1)),
        WorkTask("Init Task 3", lambda: asyncio.sleep(1))
    ]
    
    for task in init_tasks:
        await work_queue.put(task)
        print(f"Main: Enqueued {task.name} for initialization")
    
    # Start a persistent worker pool with 3 workers.
    workers = [asyncio.create_task(worker(work_queue, worker_id=i)) for i in range(3)]
    
    # Wait until all initialization tasks have been processed.
    await work_queue.join()
    print("Initialization complete, starting supervisor phase...")
    
    # === Supervisor Phase ===
    # A simple supervisor coroutine that periodically enqueues new tasks.
    async def supervisor():
        counter = 0
        while True:
            new_task = WorkTask(f"Supervisor Task {counter}", lambda: asyncio.sleep(1))
            await work_queue.put(new_task)
            print(f"Supervisor: Enqueued {new_task.name}")
            counter += 1
            await asyncio.sleep(2)  # Adjust the interval as needed.
    
    # Start the supervisor.
    supervisor_task = asyncio.create_task(supervisor())
    
    # Run the system for a while (here, 10 seconds) then shut down.
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass
    
    # Cancel the supervisor and workers for a graceful shutdown.
    supervisor_task.cancel()
    for w in workers:
        w.cancel()
    
    # Optionally, wait for cancellation to complete.
    await asyncio.gather(supervisor_task, *workers, return_exceptions=True)
    print("System shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
