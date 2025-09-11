# CLI entry
import argparse, json, csv, sys, yaml
from pathlib import Path
from src.graph import make_graph, NodeState

def run_from_csv(csv_path: str, out: str, vertical: str):
    vconf_path = f"configs/verticals/{vertical}.yml"
    vertical_config = {}
    try:
        with open(vconf_path) as f:
            vertical_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        pass

    graph = make_graph(vertical_config=vertical_config)
    outp = Path(out); outp.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path) as f, open(out, "w") as f_out:
        rdr = csv.DictReader(f)
        for row in rdr:
            state = NodeState(domain=row["domain"])
            state.company = row.get("company")
            final_dict = graph.invoke(state)
            # Convert back to NodeState object
            final = NodeState(**final_dict)
            record = {
                "domain": row["domain"],
                "company": row.get("company"),
                "vertical": row.get("vertical"),
                "card": final.card.model_dump() if final.card else None,
                "email": final.email.model_dump() if final.email else None
            }
            f_out.write(json.dumps(record) + "\n")
    print(f"Wrote {out}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="path to domains CSV")
    ap.add_argument("--out", default="data/cards_and_emails.jsonl")
    ap.add_argument("--vertical", default="dentists")
    args = ap.parse_args()
    if not args.csv:
        print("Provide --csv"); sys.exit(1)
    run_from_csv(args.csv, args.out, args.vertical)

if __name__ == "__main__":
    main()
