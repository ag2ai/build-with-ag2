import random
import asyncio

class RankingAgent:
    def __init__(self, context_variables, context_variables_lock):
        self.context_variables = context_variables
        self.context_variables_lock = context_variables_lock
        # match_history: key is tuple(sorted([hid1, hid2])) and value is a tuple:
        # (combined_version1, combined_version2)
        self.selected_pairs = [] # selected by not yet compared

    async def perform_ranking(self):
        ranking_pairs = await self.select_next_ranking_pairs()

        # try aquiring lock for each pair before comparing, only compare once
        for pair in ranking_pairs:
            hypo1, hypo2 = pair
            async with self.context_variables_lock:
                if not hypo1.lock.locked() and not hypo2.lock.locked():
                    hypo1.lock.acquire()
                    hypo2.lock.acquire()
                else:
                    continue
            await self.debate_comparison(hypo1, hypo2)
            self.record_match(hypo1, hypo2)
            async with self.context_variables_lock:
                hypo1.lock.release()
                hypo2.lock.release()

    async def tournament_comparison(self, hypo1, hypo2):
        pass

    async def debate_comparison(self, hypo1, hypo2):
        # expensive comparison
        pass

    async def select_next_ranking_pairs(self, n=3):
        """
        Select up to n ranking pairs.
        
        Process:
          1. Get the candidate list (top candidates are at the beginning).
          2. Iterate over the candidate list and for each candidate, try to select a valid second candidate.
          3. Validate that the pair has not been compared before (based on combined version numbers).
          4. Record the match using a sorted pair (to avoid future duplicate match-ups).
          5. If the top selections do not yield enough valid pairs, continue iterating.
          6. Return None if no valid pair can be found.
        """
        candidate_list = await self.sort_first_candidates()
        valid_pairs = []
        for candidate_a in candidate_list:
            candidate_b = await self.select_pair_for_first(candidate_a)
            if candidate_b is None:
                continue
            if self._is_already_compared(candidate_a, candidate_b):
                continue
            sorted_pair = tuple(sorted([candidate_a, candidate_b], key=lambda h: h.hid))
            if sorted_pair not in valid_pairs:
                valid_pairs.append(sorted_pair)
            if len(valid_pairs) >= n:
                break

        self.selected_pairs = valid_pairs
        return valid_pairs if valid_pairs else None
    


    async def record_match(self, hypo1, hypo2):
        """
        Record that these two hypotheses have been compared at their current combined versions.
        The pair is stored in sorted order (by hypothesis ID) for later retrieval.
        """
        with self.context_variables_lock:
            key = tuple(sorted([hypo1.hid, hypo2.hid]))
            self.context_variables["match_history"][key] = (hypo1.hypo_version + hypo1.review_version,
                                   hypo2.hypo_version + hypo2.review_version)


    def compute_priority_score(self, hypothesis):
        """
        Compute a steep priority score using:
          - Combined version (hypo_version + review_version)
          - The hypothesis rating
        The steep_multiplier ensures that even a small version difference produces a large score gap.
        """
        combined_version = hypothesis.hypo_version + hypothesis.review_version
        steep_multiplier = 1000  # Adjust this to control how steep the score is.
        score = hypothesis.rating + combined_version * steep_multiplier
        return score

    def proximity_score(self, hypo1, hypo2):
        """
        Placeholder for the proximity score between two hypotheses.
        For now, return a random number.
        """
        return random.random()

    async def _get_unlocked_candidates(self):
        """
        Return a list of hypotheses that are not locked.
        """
        async with self.context_variables_lock:
            return [h for h in self.context_variables['hypotheses'] if not h.lock.locked()]

    async def sort_first_candidates(self):
        """
        Build and return a single candidate list.
        Steps:
          1. Compute steep scores for each unlocked candidate.
          2. Sort them in descending order by score.
          3. Use weighted random selection to pick 3 distinct top candidates.
          4. Remove these from the sorted list and prepend them.
        """
        candidates = await self._get_unlocked_candidates()
        if not candidates:
            return []

        scored_candidates = [(h, self.compute_priority_score(h)) for h in candidates]
        sorted_candidates = sorted(scored_candidates, key=lambda x: x[1], reverse=True)
        if len(sorted_candidates) <= 3:
            return sorted_candidates
        
        # Randomly select 3 distinct candidates using weighted random selection.
        top_candidates = []
        candidate_pool = scored_candidates[:]  # Copy the list.
        attempts = 0
        while len(top_candidates) < 3 and attempts < 100 and candidate_pool:
            weights = [score for (_, score) in candidate_pool]
            chosen = random.choices([h for (h, _) in candidate_pool], weights=weights, k=1)[0]
            if chosen not in top_candidates:
                top_candidates.append(chosen)
            candidate_pool = [(h, s) for (h, s) in candidate_pool if h.hid != chosen.hid]
            attempts += 1

        return top_candidates + candidate_pool
    
    async def select_pair_for_first(self, candidate_a):
        """
        For a given first candidate, select a second candidate (from unlocked ones, excluding candidate_a).
        The score for candidate_b is based on the base priority plus a placeholder proximity score.
        """
        candidates = await self._get_unlocked_candidates()
        # Exclude candidate_a.
        candidates = [h for h in candidates if h.hid != candidate_a.hid]
        if not candidates:
            return None
        scored_candidates = []
        for h in candidates:
            base_score = self.compute_priority_score(h)
            total_score = base_score + self.proximity_score(candidate_a, h)
            scored_candidates.append((h, total_score))
        # Weighted random selection for candidate_b.
        weights = [score for (_, score) in scored_candidates]
        candidate_b = random.choices([h for (h, _) in scored_candidates], weights=weights, k=1)[0]
        return candidate_b


    def _is_already_compared(self, hypo1, hypo2):
        """
        Check whether this pair has already been compared at the same combined version.
        """
        key = tuple(sorted([hypo1.hid, hypo2.hid]))
        current_versions = (hypo1.hypo_version + hypo1.review_version,
                            hypo2.hypo_version + hypo2.review_version)
        if key in self.context_variables["match_history"]:
            if self.context_variables["match_history"][key] == current_versions:
                return True
        return False

