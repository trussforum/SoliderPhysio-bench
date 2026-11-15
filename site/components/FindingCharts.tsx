import data from "@/lib/findings.json";
import { Plot } from "@/components/Plot";

type Vars = React.CSSProperties & Record<`--${string}`, string>;

// Finding 3: how each half of the matched Rulebook pair was answered.
export function OverrideBars() {
  return (
    <Plot>
      {data.override.map((d, i) => {
        const n = d.correct + d.wrong + d.blocked;
        return (
          <div className="stack" key={d.case} style={{ "--d": `${i * 110}ms` } as Vars}>
            <span>{d.case}</span>
            <span className="row">
              {d.correct > 0 && <i style={{ width: `${(d.correct / n) * 100}%`, "--c": "var(--good)" } as Vars} title={`${d.correct} correct`} />}
              {d.wrong > 0 && <i style={{ width: `${(d.wrong / n) * 100}%`, "--c": "var(--bad)" } as Vars} title={`${d.wrong} wrong`} />}
              {d.blocked > 0 && <i style={{ width: `${(d.blocked / n) * 100}%`, "--c": "var(--drab)" } as Vars} title={`${d.blocked} blocked by content filter`} />}
            </span>
          </div>
        );
      })}
      <div className="legend">
        <span style={{ "--c": "var(--good)" } as Vars}>correct</span>
        <span style={{ "--c": "var(--bad)" } as Vars}>wrong</span>
        <span style={{ "--c": "var(--drab)" } as Vars}>blocked by filter</span>
      </div>
    </Plot>
  );
}

// Finding 5: quick-question answers (of 14 per model) whose reasoning talks about the test.
export function EvalAwareBars() {
  return (
    <Plot>
      {data.eval_aware.map((d, i) => (
        <div className="hbar" key={d.model} style={{ "--c": "var(--accent)", "--d": `${i * 60}ms` } as Vars}>
          <span>{d.model}</span>
          <i style={{ width: `${(d.n / data.eval_aware_of) * 100}%` }} title={`${d.n} of ${data.eval_aware_of} answers`} />
          <b>{d.n}</b>
        </div>
      ))}
      <div className="legend" style={{ marginTop: 10 }}>
        <span style={{ "--c": "var(--accent)" } as Vars}>answers of 14 that speculate about the test</span>
      </div>
    </Plot>
  );
}
