# Co-Scientist

This repo is an implementation of [AI Co-Scientist](https://storage.googleapis.com/coscientist_paper/ai_coscientist.pdf) using AG2.

<!-- Overall Description, authorship/references -->

## Detailed Description

<!-- More detailed description, any additional information about the use case -->

```python

# init: 3 workers in parallel
# STATE: start
# init stage: generate 3 hypotheses with full review in parallel

# STATE: 3 hypotheses with full review, and ranked.
# now supervisor decide which agent to call first.

# 1. at the beginning, we should start ranking the hypotheses. we also want to generate more hypotheses at the same time. We can have an upper hypothesis bound, (e.g. 6)
# then we should run until new hypotheses are generated and ranked.

# STATE: We have 6 hypotheses that is reviewed and ranked.

# now we should start calling meta review agents and evolution agents as workers.

# - call generation -> generate new hypotheses
# - call generation -> scientific debate -> archived hypothesis

# - call evolution agent -> refine existing hypotheses `original_hypothesis`
# - call evolution -> mutate and create new hypotheses

# - call meta review -> review existing info, and summarize upper rules to be used in all agents.

# - call ranking -> tournament ranking: 
#    - Newly added/change hypotheses is prioritized.
#    - Hypotheses with higher score is prioritized.
#    - If no change of two hypotheses, they should not be removed from the possible ranking list.

# - call review -> update review of the hypotheses. (need to have review agent to self evolve before update)
# - call review: select a different type of review to update the hypotheses.

# the version of hypothesis is determined by 1. the original hypothesis 2. the review

```

## AG2 Features

<!-- What AG2 features are demonstrated in this project? Link to AG2 documents for the features. -->

## TAGS

<!-- Add relevant tags for indexing and searching, they can be usecase or technology related -->

TAGS: swarm, graphrag, AG2-features, use-case, automation, etc.

## Installation

<Instructions for installing>

## Running the code

<!-- Code running instructions -->
<!-- Is there anything to pay attention when running the code? Any example usage?-->

## Contact

<!-- Add any helpful resources here! -->

For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: https://docs.ag2.ai/docs/Home
- Reachout to us: https://github.com/ag2ai/ag2
- Join Discord: https://discord.gg/pAbnFJrkgZ

## License

<!-- Comply with the license if the use case is modified -->
