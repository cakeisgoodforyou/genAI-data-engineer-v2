import yaml

def get_tools_description(tools: list) -> str:
    """Generate a description of available tools from LangChain tool objects."""
    descriptions = []
    for tool in tools:
        descriptions.append({
            "name": tool.name,
            "description": tool.description,
            "args": tool.args_schema.schema().get("properties", {}) if tool.args_schema else {}
        })
    return yaml.dump(descriptions)