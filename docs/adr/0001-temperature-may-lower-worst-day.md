# Temperature may lower the worst day

The execution-plan deck says a move that lowers worst-day availability is always rejected. We decided the opposite for the candidate method: early in the search, a high temperature may accept that move, and it becomes rare as the search cools. The reported schedule is always the best-so-far, so a dip is not what we hand back.

The alternative was the deck's rule, now called tightened acceptance: never accept a lower worst day, and anneal only when that worst day is unchanged. That rule stays in the study as the fallback. If a temperature run loses worst-day availability, the handover reports the tightened runs instead of keeping the looser rule.

The deck is left as presented. The handover notes the difference.
