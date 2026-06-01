from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    node_general_qa,
    node_general_router,
    route_after_router,
)
from app.graphs.discovery_graph import get_discovery_graph
from app.models.state import GraphState, SessionState


def _discovery_wrapper(state: GraphState) -> GraphState:
    graph = get_discovery_graph()
    result = graph.invoke(state)
    if isinstance(result, dict):
        return GraphState.model_validate(result)
    return result


def build_main_graph():
    g = StateGraph(GraphState)
    g.add_node("router", node_general_router)
    g.add_node("general_qa", node_general_qa)
    g.add_node("discovery", _discovery_wrapper)

    g.set_entry_point("router")
    g.add_conditional_edges(
        "router",
        route_after_router,
        {"general_qa": "general_qa", "discovery": "discovery"},
    )
    g.add_edge("general_qa", END)
    g.add_edge("discovery", END)
    # Session state is persisted in session_store; no checkpointer (avoids thread_id requirement).
    return g.compile()


_main_graph = None


def get_main_graph():
    global _main_graph
    if _main_graph is None:
        _main_graph = build_main_graph()
    return _main_graph


def run_chat_turn(session: SessionState, user_message: str) -> GraphState:
    state = GraphState(session=session, user_message=user_message)
    graph = get_main_graph()
    result = graph.invoke(state)
    if isinstance(result, dict):
        return GraphState.model_validate(result)
    return result


def run_manual_filter(session: SessionState) -> GraphState:
    from app.agents.nodes import (
        node_session_manager,
        node_ui_finalize,
        node_vehicle_search,
        node_why_recommend,
    )

    state = GraphState(
        session=session,
        user_message="",
        manual_filter_only=True,
        skip_discovery=False,
    )
    state = node_session_manager(state)
    state = node_vehicle_search(state)
    c = state.session.candidate_count
    if 5 <= c <= 7:
        state = node_why_recommend(state)
        state = node_ui_finalize(state)
    else:
        from app.agents.nodes import _update_ui_from_candidates

        _update_ui_from_candidates(state)
        state.reply = f"Found {c} matching vehicles. Adjust filters or keep chatting to narrow down."
    return state
