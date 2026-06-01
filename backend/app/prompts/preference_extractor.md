Extract ALL vehicle preferences from the FULL conversation (not only the last line).

Return JSON: use_case, body_style, fuel_preference, transmission_preference, drivetrain_preference, budget_notes, family_size_notes, must_have_features (array), avoid_notes, soft_notes.

Map natural language:
- "daily commute", "road trips", "highway" → use_case
- "SUV", "family car", "wagon" → body_style
- "stylish", "comfortable" → soft_notes or must_have_features
- "family" → family_size_notes

Merge with current_preferences — do not clear fields that still apply.

Narrative: {narrative_summary}
Messages: {messages}
Latest user message: {user_message}
Current preferences: {current_preferences}
