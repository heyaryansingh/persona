import { useState, Component } from "react";
import Dashboard from "./screens/Dashboard.jsx";
import Notebook from "./screens/Notebook.jsx";
import SwarmView from "./screens/SwarmView.jsx";
import ArgumentState from "./screens/ArgumentState.jsx";
import DependencyGraph from "./screens/DependencyGraph.jsx";
import IdeaGraph from "./screens/IdeaGraph.jsx";
import ExperimentQueue from "./screens/ExperimentQueue.jsx";
import HandoffInbox from "./screens/HandoffInbox.jsx";
import Artifacts from "./screens/Artifacts.jsx";

const SCREENS = [
  ["dashboard", "Dashboard", Dashboard],
  ["notebook", "Living Notebook", Notebook],
  ["swarm", "Swarm & Membrane", SwarmView],
  ["idea", "Idea Graph", IdeaGraph],
  ["argument", "Argument-State", ArgumentState],
  ["dependency", "Dependency Graph", DependencyGraph],
  ["experiments", "Experiment Queue", ExperimentQueue],
  ["handoff", "Human Handoff", HandoffInbox],
  ["artifacts", "Artifacts", Artifacts],
];

class ScreenErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }
  render() {
    if (this.state.error) {
      return (
        <div className="card">
          <div className="screen-title">Error</div>
          <div className="screen-lede">This screen hit an error</div>
          <p className="mono muted" style={{ whiteSpace: "pre-wrap" }}>
            {String(this.state.error?.message || this.state.error)}
          </p>
          <button className="action" onClick={() => location.reload()}>
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const [active, setActive] = useState("dashboard");
  const Screen = SCREENS.find((s) => s[0] === active)[2];
  return (
    <div className="app">
      <nav className="nav">
        <div className="brand">
          Persona<small>a mind at work · scale of reading, discipline of believing</small>
        </div>
        <div style={{ height: 14 }} />
        {SCREENS.map(([id, label]) => (
          <button
            key={id}
            className={"nav-item" + (active === id ? " active" : "")}
            onClick={() => setActive(id)}
          >
            {label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <div className="muted mono" style={{ fontSize: 10.5, lineHeight: 1.5 }}>
          seed: Alzheimer's neuroinflammation · live Europe PMC · human-gated ignition
        </div>
      </nav>
      <main className="main">
        <ScreenErrorBoundary resetKey={active}>
          <Screen />
        </ScreenErrorBoundary>
      </main>
    </div>
  );
}
