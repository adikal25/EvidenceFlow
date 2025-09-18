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
            final = NodeState(**final_dict)
            
            
            card_data = None
            if final.card:
                card_data = final.card.model_dump()
                if 'canonical_url' in card_data:
                    card_data['canonical_url'] = str(card_data['canonical_url'])
                if 'first_seen' in card_data:
                    card_data['first_seen'] = card_data['first_seen'].isoformat()
                if 'last_seen' in card_data:
                    card_data['last_seen'] = card_data['last_seen'].isoformat()
            
            email_data = None
            if final.email:
                email_data = final.email.model_dump()
            
            record = {
                "domain": row["domain"],
                "company": row.get("company"),
                "vertical": row.get("vertical"),
                "card": card_data,
                "email": email_data
            }
            f_out.write(json.dumps(record) + "\n")

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
