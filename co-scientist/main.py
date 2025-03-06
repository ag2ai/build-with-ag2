import asyncio
import time
import json
from dataclasses import dataclass
from typing import Callable, Awaitable, Any, List, Dict, Optional
import aiofiles 
from dataclasses import dataclass, field
import logging
from collections import deque

from utils import setup_logger, logger
logger = setup_logger("system.log")
logger.setLevel(logging.DEBUG)

from task_manager import WorkTask, TaskManager, worker, checkpoint_writer
from ranking_agent import RankingAgent
from hypo_objects import Hypothesis, Review

class GenerationAgent:
    def __init__(self, context_variables: Dict, context_variables_lock: asyncio.Lock):
        self.context_variables = context_variables
        self.context_variables_lock = context_variables_lock
        pass

    async def web_search(self) -> str:
        # TODO 3: Fill in the web search logic
        # perform web search action
        await asyncio.sleep(1)

        # acquire lock and update context variables
        async with self.context_variables_lock:
            self.context_variables["related_articles"] = [
                {"name": "article1", "review": "review1", "link": "link1"},
                {"name": "article2", "review": "review2", "link": "link2"},
                {"name": "article3", "review": "review3", "link": "link3"}
            ]
        print("Web search completed", self.context_variables_lock.locked())

    async def generate_hypothesis(self) -> Hypothesis:
        """
        Generate a hypothesis based on the context variables.
        Input fields: goal, preferences, source_hypothesis (if any), instructions, articles_with_reasoning (from web search)
        """
        # TODO 4: Fill in the hypothesis generation logic
        # TODO 4.2: do intial review here directly. If failed, append to discarded_hypotheses
        await asyncio.sleep(3)
        
        async with self.context_variables_lock:
            print(f"Hypothesis {self.context_variables['hid_counter']} generated")
            new_hypothesis = Hypothesis(
                hid=str(self.context_variables["hid_counter"]),
                original_hypothesis=f"Original hypothesis {self.context_variables['hid_counter']}", # TODO 4.1: fill in the original hypothesis
                selected_articles=self.context_variables["related_articles"] # TODO 4.2: fill in the selected articles if any
            )
            self.context_variables['hid_counter'] += 1
            self.context_variables['hypotheses'].append(new_hypothesis)
        

    async def multi_agent_debate(self, hypothesis: Hypothesis):
        """
        Perform a multi-agent debate on the hypothesis with the given hid.
        """
        # TODO 5: Fill in the multi-agent debate logic, debate_logs
        async with hypothesis.lock:
            # perform debate action here
            await asyncio.sleep(1)

            # acquire lock for the context variables at the same time to update the hypothesis
            async with self.context_variables_lock:
                hypothesis.finalized_hypothesis = f"Finalized hypothesis {hypothesis.hid}" # TODO 5.1: fill in the finalized hypothesis

class ReflectionAgent:
    def __init__(self, context_variables, context_variables_lock):
        self.context_variables = context_variables
        self.context_variables_lock = context_variables_lock
    
    # Perform initial review on the hypothesis
    # async def initial_review(self, hid: str):

    async def perform_full_review(self, hypothesis: Hypothesis):
        # TODO 6: Fill in the full review logic
        async with hypothesis.lock:
            # perform full review here
            await asyncio.sleep(1)
            print(f"Full review completed for hypothesis {hypothesis.hid}")

            # acquire lock for the context variables at the same time to update the hypothesis
            async with self.context_variables_lock:
                hypothesis.review.full_review = f"Perform full review on hypothesis {hypothesis.hid}"
                hypothesis.review_version += 1

    async def deep_verify_review(self, hypothesis: Hypothesis):
        pass

    async def observe_review(self, hypothesis: Hypothesis):
        pass

    async def simulation_review(self, hypothesis: Hypothesis):
        pass

    async def get_review_overview(self, hypothesis: Hypothesis):
        pass


class EvolutionAgent:
    def __init__(self, context_variables, context_variables_lock):
        self.context_variables = context_variables
        self.context_variables_lock = context_variables_lock

    async def refine_hypothesis(self, hypothesis: Hypothesis):
        pass

    async def mutate_hypothesis(self, context_variables):
        new_hypothesis = Hypothesis()
        return new_hypothesis
    
class MetaReviewAgent:
    def __init__(self, context_variables, context_variables_lock):
        self.context_variables = context_variables
        self.context_variables_lock = context_variables_lock

    async def review(self, context_variables):
        # update constraints ?
        pass


class Supervisor:
    def __init__(self, context_variables, context_variables_lock):
        self.context_variables = context_variables
        self.context_variables_lock = context_variables_lock

    async def initial_stage(self, task_manager:"TaskManager", generation_agent: GenerationAgent, reflection_agent: ReflectionAgent):
        """
        Dynamically add generate_hypothesis and generate_full_review tasks until
        there are 3 valid hypotheses with full review.
        """
        logger.info("Start initial stage")
        async def count_hypotheses(with_full_review=False):
            if not with_full_review:
                return len(self.context_variables['hypotheses'])

            count = 0
            async with self.context_variables_lock:
                for hypothesis in self.context_variables['hypotheses']:
                    if hypothesis.review.full_review != "":
                        count += 1
            return count

        # Continue until we have at least 3 fully reviewed, valid hypotheses.
        while await count_hypotheses(with_full_review=True) < 3:
            for hypothesis in self.context_variables['hypotheses']:
                if hypothesis.lock.locked(): # if locked, potentially being reviewed, skip
                    continue
                if hypothesis.review.full_review == "":
                    # Enqueue a full review task if not already in progress
                    logger.info(f"Supervisor: Add full review task for hypothesis {hypothesis.hid}")
                
                    await task_manager.add_task(WorkTask(
                        name="perform_full_review",
                        coro=lambda hypothesis=hypothesis: reflection_agent.perform_full_review(hypothesis)
                    ))
            
            # If still not enough unchecked hypotheses, generate a new one.
            # make sure only 3 generate_hypothesis task are in the queue
            hypo_count = await count_hypotheses()
            running_hypo_count = await task_manager.get_task_count_with("generate_hypothesis")
            if hypo_count + running_hypo_count < 3:
                logger.info(f"Supervisor: Add generate hypothesis task: {self.context_variables['hid_counter']}")
                await task_manager.add_task(WorkTask(
                    name="generate_hypothesis",
                    coro=lambda: generation_agent.generate_hypothesis()
                ))            
            await asyncio.sleep(1)

    async def select_worker(self, 
        task_manager:"TaskManager",
        generation_agent: GenerationAgent,
        ranking_agent: RankingAgent,
        reflection_agent: ReflectionAgent,
        evolution_agent: EvolutionAgent,
        meta_review_agent: MetaReviewAgent
    ):
        # use LLM to decide the next worker
        # 1. info from task_manager: pending_tasks, and running tasks.
        async with self.context_variables_lock:
            unlocked = [h for h in self.context_variables['hypotheses'] if not h.lock.locked()]
        
        if len(unlocked) == 0:
            # all hypotheses are locked, perform meta review 
            # TODO: perform summary
            # TODO feature: user can send an async message to an agent for improvement

            return WorkTask(name="meta_review", coro=lambda: meta_review_agent.review(self.context_variables))
    
        instruction = """
## Description of Each Agent

## Unlocked Hypotheses (Can be worked on)

## Options
For those unlocked hypotheses, you can choose to:
1. Perform a type of review 
2. Perform a evolution action on one of the hypothesis
3. Generate a new hypothesis using the generation agent
4. Generate a new hypothesis using the evolution agent
5. Perform Ranking action: possible pairs to compare: ...

Please select the next action, and the hid of the hypothesis.
"""

        return WorkTask(name="generate_hypothesis", coro=lambda: generation_agent.generate_hypothesis())


# Example main function that sets up the worker pool, a producer, and the checkpoint writer.
async def main():
    CONTEXT_VARIABLES = {
        "goal": "", # by the user at the beginning
        "configuration": { # parsed from the user's input by LLM
            "preferences": "",
            "idea_attributes": "",
            # "constraints": "",
        },
        "hid_counter": 0, # counter for hypothesis id

        "notes": "", # from the user later giving feedback
        "instructions": "", # from meta review agent? 

        # List[Dict] {"name": "article_name", "review": "literature_review", "link": "article_link"}
        "related_articles": [], 

        # list of hypothesis
        "hypotheses": [], # List[Hypothesis]
        "discarded_hypotheses": [], # List[Hypothesis]

        # ranking
        "pairwise_comparisons": [], #  List[Dict] {"hypothesis1": "hypothesis1_id", "hypothesis2": "hypothesis2_id", "winner": "hypothesis1_id"}
    }
    CONTEXT_VARIABLES_LOCK = asyncio.Lock()

    # 1. accept goal from user and parse constraints
    # TODO 1: accept user input and parse constraints

    # temporary hardcoded values
    CONTEXT_VARIABLES["goal"] = "I want to do reasearch on AI"
    CONTEXT_VARIABLES["configuration"] = {
        "preferences": "I want to focus on LLM routing",
        "idea_attributes": "Novelty, Feasibility",
        "constraints": "should be correct, should be novel."
    }

    # 2. Resume from checkpoint
    # TODO 2: Resume from checkpoint if available.
    
    # 3. initialize agents
    generation_agent = GenerationAgent(CONTEXT_VARIABLES, CONTEXT_VARIABLES_LOCK)
    ranking_agent = RankingAgent(CONTEXT_VARIABLES, CONTEXT_VARIABLES_LOCK)
    reflection_agent = ReflectionAgent(CONTEXT_VARIABLES, CONTEXT_VARIABLES_LOCK)
    evolution_agent = EvolutionAgent(CONTEXT_VARIABLES, CONTEXT_VARIABLES_LOCK)
    meta_review_agent = MetaReviewAgent(CONTEXT_VARIABLES, CONTEXT_VARIABLES_LOCK)
    supervisor = Supervisor(CONTEXT_VARIABLES, CONTEXT_VARIABLES_LOCK)
    await generation_agent.web_search() # perform initial web search to prepare k articles

    # -------------------------
    # 4. Start the worker pool.
    task_manager = TaskManager()
    workers = [asyncio.create_task(worker(task_manager, worker_id=i)) for i in range(3)] # Start 3 workers
    check_point_interval = 5
    checkpoint_task = asyncio.create_task(checkpoint_writer(task_manager, check_point_interval))

    # -------------------------
    # 5. Start the initialization phase
    # dynamic add generate_hypothesi and generate_full_review tasks unitil there are 3 valid hypotheses with full review in the list
        # generate_hypothesis can get a discared hypothesis, put new generate task dynamically until there are 3 valid hypotheses in the list, also put a full reivew task for each hypothesis

    # use supervisor to dynamically add tasks
    await supervisor.initial_stage(task_manager, generation_agent, reflection_agent)

    # -------------------------
    # 6. Start the main stage
    # Set a maximum runtime of 60 seconds
    # start_time = time.time()
    # max_runtime = 60

    # while time.time() - start_time < max_runtime:
    #     while task_manager.pending_tasks.qsize() < 5:
    #         # select the next worker
    #         next_worker = await supervisor.select_worker(
    #             task_manager, generation_agent, ranking_agent, reflection_agent, evolution_agent, meta_review_agent
    #         )
    #         await task_manager.add_task(next_worker)
    #     await asyncio.sleep(1)

    # if time.time() - start_time >= max_runtime:
    #     logger.info("Maximum runtime reached, stopping adding new tasks.")

    # -------------------------
    # 7. Shutdown the system
    logger.debug("Ending stage: 1. Waiting for all tasks in queue to finish...")
    while task_manager.pending_tasks.qsize() > 0:
        await asyncio.sleep(1)
    
    logger.debug("Ending stage: 2. Waiting for a final checkpoint after all tasks are done...")
    # Wait for the checkpoint writer to finish writing the logs for the last time.
    try:
        await asyncio.sleep(check_point_interval + 0.5)
    except asyncio.CancelledError:
        pass

    logger.debug("Ending stage: 3. Shutting down the system.")
    checkpoint_task.cancel()
    for w in workers:
        w.cancel()
    await asyncio.gather(checkpoint_task, *workers, return_exceptions=True)
    logger.debug("System shutdown complete.")


# Reflection: By analyzing reviewed hypotheses and results of the tournament conducted by the Ranking agent, the Reflection agent identifies recurring issues and improvement opportunities, refining its reviews accordingly.

if __name__ == "__main__":
    asyncio.run(main())