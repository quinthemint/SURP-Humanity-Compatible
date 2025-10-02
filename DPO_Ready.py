import json, argparse
from pathlib import Path

def clean(s):
    return " ".join(s.split()).strip()

def pick(row):
    win_is_a = row["choice"] == "A"
    winner_orig = row["a_text"] if win_is_a else row["b_text"]
    loser_orig  = row["b_text"] if win_is_a else row["a_text"]
    if row.get("ethical", False):
        winner = row.get("rewrite", "").strip()
        loser  = loser_orig
    else:
        winner = winner_orig
        loser  = loser_orig
    return clean(row["prompt"]), clean(winner), clean(loser)

def valid(prompt, chosen, rejected):
    if not prompt or not chosen or not rejected: return False
    if chosen == rejected: return False
    if len(chosen) < 5 or len(rejected) < 5: return False
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default="curated.jsonl")
    ap.add_argument("--output", type=str, default="dpo_pairs.jsonl")
    args = ap.parse_args()

    seen = set()
    kept = 0
    with open(args.input, "r", encoding="utf-8") as fin, open(args.output, "w", encoding="utf-8") as fout:
        for line in fin:
            row = json.loads(line)
            pid = row.get("pid")
            if pid in seen: continue
            try:
                prompt, chosen, rejected = pick(row)
            except Exception:
                continue
            if not row.get("ethical", False) and row.get("rewrite","none") != "none": 
                continue
            if valid(prompt, chosen, rejected):
                fout.write(json.dumps({"prompt": prompt, "chosen": chosen, "rejected": rejected}, ensure_ascii=False) + "\n")
                kept += 1
                if pid: seen.add(pid)
    print(f"wrote {kept} pairs to {args.output}")

if __name__ == "__main__":
    main()
