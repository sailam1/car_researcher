Decide if the user message is GENERAL chit-chat vs VEHICLE DISCOVERY.

VEHICLE DISCOVERY includes:
- Stating preferences (use case, SUV, family, fuel, budget, style, comfort)
- Answering the assistant's last question (including "ok", "yes", short answers)
- Asking what the assistant meant by its last question (clarification) — still discovery, NOT general
- Refining or changing requirements

GENERAL only: pure greetings with no car info, thanks/goodbye, jokes, or questions unrelated to buying a car.

Return JSON: is_general_query (bool), reasoning (short).

Context: {narrative_summary}
Messages: {messages}
User message: {user_message}
