import { describe, it, expect } from "vitest";
import { GateNodeWeatherAgentBuildAWeatherAgent } from "../agent";

describe("gate_node_weather_agent_build_a_weather", () => {
  it("invoke returns ok", async () => {
    const agent = new GateNodeWeatherAgentBuildAWeatherAgent();
    const out = await agent.invoke({ k: "v" });
    expect(out.status).toBe("ok");
  });
});
