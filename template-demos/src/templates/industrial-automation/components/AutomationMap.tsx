"use client";

import { useState } from "react";
import { Box, Camera, Factory, MoveRight, PackageCheck } from "lucide-react";
import styles from "./Automation.module.css";

const nodes = [
  { id: "infeed", code: "01", label: "Infeed", icon: Box, signal: "Part identity + arrival", detail: "Present the right workpiece in a known orientation before motion begins." },
  { id: "vision", code: "02", label: "Vision", icon: Camera, signal: "Position + acceptability", detail: "Control the image, define the decision and make uncertainty visible." },
  { id: "robot", code: "03", label: "Robot", icon: MoveRight, signal: "Handling + state", detail: "Coordinate reach, payload, tooling and safe recovery around the process." },
  { id: "process", code: "04", label: "Process", icon: Factory, signal: "Cycle + machine state", detail: "Confirm machine readiness and expose the real production constraint." },
  { id: "outfeed", code: "05", label: "Outfeed", icon: PackageCheck, signal: "Disposition + record", detail: "Release, divert or hold each result with an explicit production record." },
] as const;

export function AutomationMap() {
  const [active, setActive] = useState<(typeof nodes)[number]>(nodes[2]);

  return <div className={styles.systemMap}>
    <div className={styles.mapHead}><span>INTERACTIVE LINE MAP / DEMO</span><small>Select a system node</small></div>
    <div className={styles.mapTrack} role="list" aria-label="Automation line stages">
      {nodes.map((node, index) => {
        const Icon = node.icon;
        const selected = active.id === node.id;
        return <div className={styles.mapStepWrap} key={node.id}>
          <button type="button" className={selected ? styles.mapNodeActive : styles.mapNode} aria-pressed={selected} onClick={() => setActive(node)}>
            <span>{node.code}</span><Icon /><b>{node.label}</b>
          </button>
          {index < nodes.length - 1 && <div className={styles.mapConnector}><i /><i /><i /><ArrowMark /></div>}
        </div>;
      })}
    </div>
    <div className={styles.mapReadout} aria-live="polite"><span>{active.code} / {active.label.toUpperCase()}</span><strong>{active.signal}</strong><p>{active.detail}</p><small>Illustrative architecture — confirm every interface during discovery.</small></div>
  </div>;
}

function ArrowMark() {
  return <span aria-hidden="true">→</span>;
}
