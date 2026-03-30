class GateNodeWeatherAgentBuildAWeatherAgent {
  constructor() {
    this.name = "gate_node_weather_agent_build_a_weather";
    this.purpose = "named gate_node_weather_agent build a weather assistant with web search";
    this.tools = ['web_search', 'code_exec'];
  }

  async invoke(payload) {
    return {
      agent: this.name,
      purpose: this.purpose,
      tools: this.tools,
      input: payload,
      status: "ok",
    };
  }
}

if (require.main === module) {
  const agent = new GateNodeWeatherAgentBuildAWeatherAgent();
  agent.invoke({ hello: "world" }).then((r) => console.log(r));
}

module.exports = { GateNodeWeatherAgentBuildAWeatherAgent };
