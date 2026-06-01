Generate exactly ONE follow-up question for vehicle discovery. Reply with plain text only (no JSON, no markdown).

CRITICAL RULES:
- Acknowledge what the user already told us (see known_preferences). Do NOT re-ask use case if they said commute, road trips, SUV, family, stylish, or comfortable.
- NEVER repeat the same topic as last_question unless the user's answer was empty or "ok" only.
- Ask about the FIRST item in missing_dimensions only.
- Be concise, friendly, and specific (not vague "what kind of car").
- If candidate_count is 5-7, ask to confirm the shortlist instead of new filters.

Phase: {discovery_phase}
Known preferences: {known_preferences}
Missing dimensions (ask the first one only): {missing_dimensions}
Already asked dimensions: {asked_dimensions}
Candidate count: {candidate_count}
Last question: {last_question}
Last user message: {user_message}
Narrative: {narrative_summary}
