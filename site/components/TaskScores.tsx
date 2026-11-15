import data from "@/lib/soldier.json";
import { Mark } from "@/components/Mark";
import { Plot } from "@/components/Plot";

// Scores shown on a 0–1 scale (value / 100). Best value per column is bolded
// on the rounded numbers actually displayed, so ties and rounding stay honest.
const unit = (x: number, d: number) => Number((x / 100).toFixed(d));

const rows = [...data.models]
  .sort((a, b) => b.overall - a.overall)
  .map((m) => ({
    m,
    index: unit(m.overall, 3),
    keep: unit(m.keep, 2),
    rulebook: unit(m.rulebook, 2),
    research: unit(m.research, 2),
    calls: m.calls,
    cells: m.cells,
    cost: m.cost,
  }));

const max = (k: "index" | "keep" | "rulebook" | "research" | "calls" | "cells") =>
  Math.max(...rows.map((r) => r[k]));
const best = {
  index: max("index"), keep: max("keep"), rulebook: max("rulebook"),
  research: max("research"), calls: max("calls"), cells: max("cells"),
  cost: Math.min(...rows.map((r) => r.cost)),
};

type HeatCol = "index" | "keep" | "rulebook" | "research";

const colRange = (k: HeatCol | "cost") => {
  const vals = rows.map((r) => r[k]);
  return { min: Math.min(...vals), max: Math.max(...vals) };
};

/** 0 = column worst, 1 = column best (cost uses inverted scale). */
const heatStrength = (k: HeatCol | "cost", value: number) => {
  const { min, max } = colRange(k);
  if (max <= min) return 1;
  const t = (value - min) / (max - min);
  return k === "cost" ? 1 - t : t;
};

/** Light amber tile. Capped so the number stays dark ink on every cell. */
const heatBg = (strength: number) => {
  const a = 0.07 + strength * 0.34;
  return `rgba(180, 83, 9, ${a.toFixed(3)})`;
};

const Num = ({
  isBest,
  heat,
  children,
}: {
  isBest: boolean;
  heat?: number;
  children: React.ReactNode;
}) => (
  <td className="num">
    <span
      className={heat !== undefined ? `heat-cell${isBest ? " is-best" : ""}` : `heat-plain${isBest ? " is-best" : ""}`}
      style={heat !== undefined ? { backgroundColor: heatBg(heat) } : undefined}
    >
      {children}
    </span>
  </td>
);

export function TaskScores() {
  return (
    <Plot>
    <table className="dt dt-heat">
      <thead>
        <tr>
          <th>Model</th>
          <th className="num">Index</th>
          <th className="num">Keep/Pull</th>
          <th className="num">Rulebook</th>
          <th className="num">Research</th>
          <th className="num">Calls right</th>
          <th className="num">Card cells</th>
          <th className="num">Cost</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.m.id} className="row-in" style={{ "--d": `${i * 40}ms` } as React.CSSProperties}>
            <td>
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Mark provider={r.m.provider} />{r.m.name}</span>
            </td>
            <Num isBest={r.index === best.index} heat={heatStrength("index", r.index)}>
              {r.index.toFixed(3)}
            </Num>
            <Num isBest={r.keep === best.keep} heat={heatStrength("keep", r.keep)}>
              {r.keep.toFixed(2)}
            </Num>
            <Num isBest={r.rulebook === best.rulebook} heat={heatStrength("rulebook", r.rulebook)}>
              {r.rulebook.toFixed(2)}
            </Num>
            <Num isBest={r.research === best.research} heat={heatStrength("research", r.research)}>
              {r.research.toFixed(2)}
            </Num>
            <Num isBest={r.calls === best.calls}>{`${r.calls}/12`}</Num>
            <Num isBest={r.cells === best.cells}>{`${r.cells}/8`}</Num>
            <Num isBest={r.cost === best.cost} heat={heatStrength("cost", r.cost)}>
              {`$${r.cost.toFixed(2)}`}
            </Num>
          </tr>
        ))}
      </tbody>
    </table>
    </Plot>
  );
}
