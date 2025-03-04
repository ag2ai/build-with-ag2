import random

class RankingAgent:
    def __init__(self, context_variables, context_variables_lock):
        self.context_variables = context_variables
        self.context_variables_lock = context_variables_lock
        self.match_history = {}

    def is_already_compared(self, hypo1, hypo2):
        """
        Check whether this pair has already been compared at the same version.
        """
        key = tuple(sorted([hypo1.hid, hypo2.hid]))
        current_versions = (hypo1.hypo_version + hypo1.review_version,
                            hypo2.hypo_version + hypo2.review_version)
        if key in self.match_history:
            if self.match_history[key] == current_versions:
                return True
        return False

    def record_match(self, hypo1, hypo2):
        """
        Record that these two hypotheses have been compared at their current versions.
        """
        key = tuple(sorted([hypo1.hid, hypo2.hid]))
        self.match_history[key] = (hypo1.hypo_version + hypo1.review_version,
                                   hypo2.hypo_version + hypo2.review_version)

    def compute_priority(self, hypothesis):
        """
        Compute a steep priority score using:
          - Combined version (hypo_version + review_version)
          - The hypothesis rating
        The steep_multiplier ensures that small version differences yield large score gaps.
        """
        combined_version = hypothesis.hypo_version + hypothesis.review_version
        steep_multiplier = 1000  # Adjust this to control how steep the score is.
        score = hypothesis.rating + combined_version * steep_multiplier
        return score

    def proximity_score(self, hypo1, hypo2):
        """
        Placeholder for proximity score between two hypotheses.
        Return a random number for now.
        """
        return random.random()

    async def get_unlocked_candidates(self):
        """
        Return a list of hypotheses that are not locked.
        """
        async with self.context_variables_lock:
            return [h for h in self.context_variables['hypotheses'] if not h.lock.locked()]

    async def select_first_candidates(self):
        """
        From the unlocked candidates, compute their steep scores and then use weighted
        random selection to pick 3 distinct candidates.
        Also, record the full sorted list (by score) for later use.
        """
        candidates = await self.get_unlocked_candidates()
        if not candidates:
            return [], []
        # Compute score for each candidate.
        scored_candidates = [(h, self.compute_priority(h)) for h in candidates]
        # Sort candidates descending by score (for backup selection).
        sorted_candidates = sorted(scored_candidates, key=lambda x: x[1], reverse=True)
        # Use weighted random selection to pick 3 distinct candidates.
        first_candidates = []
        candidate_pool = scored_candidates[:]  # work on a copy
        attempts = 0
        while len(first_candidates) < 3 and attempts < 100 and candidate_pool:
            # Extract weights and candidates.
            weights = [score for (_, score) in candidate_pool]
            chosen = random.choices([h for (h, _) in candidate_pool], weights=weights, k=1)[0]
            if chosen not in first_candidates:
                first_candidates.append(chosen)
            # Remove chosen candidate so we don't pick it again.
            candidate_pool = [(h, s) for (h, s) in candidate_pool if h.hid != chosen.hid]
            attempts += 1
        return first_candidates, sorted_candidates

    async def select_pair_for_first(self, candidate_a):
        """
        For the given first candidate, select a second candidate from unlocked ones (excluding candidate_a).
        The score for candidate_b is based on the base priority plus an extra proximity score (placeholder).
        """
        candidates = await self.get_unlocked_candidates()
        # Exclude candidate_a.
        candidates = [h for h in candidates if h.hid != candidate_a.hid]
        if not candidates:
            return None
        scored_candidates = []
        for h in candidates:
            base_score = self.compute_priority(h)
            # Add proximity score relative to candidate_a.
            total_score = base_score + self.proximity_score(candidate_a, h)
            scored_candidates.append((h, total_score))
        # Weighted random selection for candidate_b.
        weights = [score for (_, score) in scored_candidates]
        candidate_b = random.choices([h for (h, _) in scored_candidates], weights=weights, k=1)[0]
        return candidate_b

    async def select_next_ranking_pairs(self, n=3):
        """
        Select up to n ranking pairs.
        
        Process:
         1. Get unlocked candidates and compute steep scores.
         2. Use weighted random selection to pick 3 first candidates (record these as top picks)
            and also keep a sorted list of the remaining candidates.
         3. For each first candidate, select a second candidate (using an extra proximity score).
         4. Validate that the pair has not been compared before (using combined version numbers).
         5. If valid, record the match and add the pair.
         6. If none of the top 3 yield a valid pair, go through the sorted list.
         7. If no valid pair is available at all, return None.
        """
        first_candidates, sorted_candidates = await self.select_first_candidates()
        valid_pairs = []
        # Try the top 3 first candidates.
        for candidate_a in first_candidates:
            candidate_b = await self.select_pair_for_first(candidate_a)
            if candidate_b is None:
                continue
            if self.is_already_compared(candidate_a, candidate_b):
                continue
            self.record_match(candidate_a, candidate_b)
            valid_pairs.append((candidate_a, candidate_b))
            if len(valid_pairs) >= n:
                break
        # If fewer than n pairs have been found, try going through the sorted list.
        if len(valid_pairs) < n:
            for (candidate_a, _) in sorted_candidates:
                # Skip if already selected as first candidate.
                if candidate_a in [pair[0] for pair in valid_pairs]:
                    continue
                if candidate_a.lock.locked():
                    continue
                candidate_b = await self.select_pair_for_first(candidate_a)
                if candidate_b is None:
                    continue
                if self.is_already_compared(candidate_a, candidate_b):
                    continue
                self.record_match(candidate_a, candidate_b)
                valid_pairs.append((candidate_a, candidate_b))
                if len(valid_pairs) >= n:
                    break
        return valid_pairs if valid_pairs else None
