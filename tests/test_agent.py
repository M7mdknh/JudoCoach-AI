from app.agents.research_agent import build_agent


def test_agent_created():
    agent = build_agent()
    assert agent is not None


def test_agent_has_no_save_tool_before_approval():
    agent = build_agent(approved_to_save=False)
    tool_names = {tool.metadata.name for tool in agent.tools}

    assert "save_report" not in tool_names


def test_agent_has_save_tool_after_approval():
    agent = build_agent(approved_to_save=True)
    tool_names = {tool.metadata.name for tool in agent.tools}

    assert "save_report" in tool_names
