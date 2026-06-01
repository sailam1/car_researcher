from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    node_enough_data,
    node_message_info_analyzer,
    node_preference_extractor,
    node_question_generator,
    node_session_manager,
    node_ui_finalize,
    node_vehicle_search,
    node_why_recommend,
    route_after_enough_data,
)
from app.models.state import GraphState


def build_discovery_graph():
    g = StateGraph(GraphState)

    g.add_node("preference_extractor", node_preference_extractor)
    g.add_node("session_manager", node_session_manager)
    g.add_node("vehicle_search", node_vehicle_search)
    g.add_node("message_info_analyzer", node_message_info_analyzer)
    g.add_node("enough_data", node_enough_data)
    g.add_node("question_generator", node_question_generator)
    g.add_node("why_recommend", node_why_recommend)
    g.add_node("ui_finalize", node_ui_finalize)

    g.set_entry_point("preference_extractor")
    g.add_edge("preference_extractor", "session_manager")
    g.add_edge("session_manager", "vehicle_search")
    g.add_edge("vehicle_search", "message_info_analyzer")
    g.add_edge("message_info_analyzer", "enough_data")
    g.add_conditional_edges(
        "enough_data",
        route_after_enough_data,
        {
            "question": "question_generator",
            "finalize": "why_recommend",
        },
    )
    g.add_edge("question_generator", END)
    g.add_edge("why_recommend", "ui_finalize")
    g.add_edge("ui_finalize", END)

    return g.compile()


discovery_graph = None


def get_discovery_graph():
    global discovery_graph
    if discovery_graph is None:
        discovery_graph = build_discovery_graph()
    return discovery_graph
