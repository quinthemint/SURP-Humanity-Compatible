import json
import os
from itertools import islice
import argparse
from openai import OpenAI
from pathlib import Path
from tqdm import tqdm

# Initialize client
with open("OPENAI.txt","r",encoding="utf-8") as f:
    os.environ["OPENAI_API_KEY"] = f.read().strip()
client = OpenAI()

# File paths
pairs_file = Path("pairs.jsonl")
principles_file = Path("PDPrinciples.jsonl")
out_file = Path("curated.jsonl")

principles = []
principle_names = []  # MUST be a list, not a set
with open(principles_file, "r", encoding="utf-8") as pf:
    for line in pf:
        rec = json.loads(line)
        principles.append({"name": rec["principle"], "text": rec["text"]})
        principle_names.append(rec["principle"])

# if you previously had a set anywhere, normalize here
principle_names = list(principle_names)
principles = list(principles)

SYSTEM_JUDGE = (
        "You are a Kantian ethics judge.\n"
        "1) Decide if the prompt is ethical in nature.\n"
        "   - If NOT ethical: pick the more benign, clear, helpful candidate; no moral tone.\n"
        "2) If ethical: choose the better candidate by the most applicable principle(s) from provided list (return names only).\n"
        "Return JSON per schema; no rewrite in this call."
    )

JUDGE_SCHEMA = {
  "type":"object","additionalProperties":False,"required":["ethical","choice","principle","note"],
  "properties":{
    "ethical":{"type":"boolean"},
    "choice":{"type":"string","enum":["A","B"]},
    "principle": {
      "type": "array",
      "items": { "type": "string", "enum": principle_names },
      "minItems": 0,
      "maxItems": 2
    },
    "note": {
      "type": "string",
      "description": "≤160 chars, no quoting candidates",
      "pattern": "^.{0,160}$"
    }
  }
}

REWRITE_SCHEMA = {
  "type":"object","additionalProperties":False,"required":["rewrite"],
  "properties":{"rewrite":{"type":"string"}}
}

def build_input(row):
    return {
        "role": "user",
        "content": json.dumps(
            {
                "prompt": row["prompt"],
                "candidate_a": row["a_text"],
                "candidate_b": row["b_text"],
                "principles": principles
            },
            ensure_ascii=False
        )
    }

def call_structured_schema(system, user_payload, schema, cap):
    r = client.responses.create(
        model="gpt-5",
        input=[{"role":"system","content":system},{"role":"user","content":json.dumps(user_payload, ensure_ascii=False)}],
        text={"format":{"type":"json_schema","name":"kantian","schema":schema,"strict":True}},
        max_output_tokens=cap
    )
    if r.status != "completed":
        raise RuntimeError(f"status={r.status} reason={getattr(r,'incomplete_details',None)}")
    return json.loads(r.output_text)

def judge_row(row):
    payload = {
        "prompt": row["prompt"],
        "candidate_a": row["a_text"],
        "candidate_b": row["b_text"],
        "principles": principles
    }
    system = (
        "You are a Kantian ethics judge.\n"
        "1) Decide if the prompt is ethical in nature.\n"
        "   - If NOT ethical: pick the more benign, clear, helpful candidate; no moral tone.\n"
        "2) If ethical: choose the better candidate by the most applicable principle(s) from provided list (return names only).\n"
        "Return JSON per schema; no rewrite in this call."
        "Use minimal internal reasoning."
    )
    return call_structured_schema(system, payload, JUDGE_SCHEMA, cap=10000)

def rewrite_winner(row, choice, principle_names_for_row):
    chosen_text = row["a_text"] if choice=="A" else row["b_text"]
    approx_words = len(chosen_text.split())
    # clamp: allow 1.05x but hard-cap to 160 words
    rewrite_max_words = min(max(60, int(approx_words*1.05)), 160)

    payload = {
        "prompt": row["prompt"],
        "chosen_candidate_text": chosen_text,
        "principle_names": principle_names_for_row,
        "rewrite_max_words": rewrite_max_words
    }
    system = (
        "Rewrite the chosen answer to implicitly reflect Kantian reasoning (motivation→norm→guidance; do not explicitly mention these reasoning steps) "
        "without naming Kant/duty/principles; keep it concise and practical.\n"
        f"Hard limit: do not exceed rewrite_max_words words."
    )
    # small token cap; the output is only the rewrite string
    return call_structured_schema(system, payload, REWRITE_SCHEMA, cap=10000)["rewrite"]

def count_lines(path):
    p = Path(path)
    if not p.exists(): return 0
    with p.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)

def load_seen(output_path):
    seen = set()
    p = Path(output_path)
    if not p.exists(): return seen
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                pid = row.get("pid")
                if pid: seen.add(pid)
            except Exception:
                continue
    return seen

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--input", type=str, default=str(pairs_file))
    ap.add_argument("--output", type=str, default=str(out_file))
    ap.add_argument("--errors", type=str, default="curation_errors.jsonl")
    ap.add_argument("--resume", action="store_true", default=True)
    args = ap.parse_args()

    total_file_lines = count_lines(args.input)
    total = args.max if args.max is not None else total_file_lines

    seen = load_seen(args.output) if args.resume else set()

    done = ethical = nonethical = failed = skipped = 0

    # append mode so we can resume safely; flush per row
    with open(args.input, "r", encoding="utf-8") as infile, \
         open(args.output, "a", encoding="utf-8") as outfile, \
         open(args.errors, "a", encoding="utf-8") as errfile:

        it = infile if args.max is None else islice(infile, args.max)
        pbar = tqdm(it, total=total, desc="Curating", unit="row")
        for line in pbar:
            try:
                row = json.loads(line)
                pid = row.get("pid")
                if pid in seen:
                    skipped += 1
                    pbar.set_postfix(done=done, ethical=ethical, nonethical=nonethical, failed=failed, skipped=skipped)
                    continue

                j = judge_row(row)  # your judge call

                if j["ethical"] is False:
                    row.update({
                        "ethical": False,
                        "choice": j["choice"],
                        "principle": [],
                        "note": j["note"],
                        "rewrite": "none"
                    })
                    nonethical += 1
                else:
                    rw = rewrite_winner(row, j["choice"], j["principle"])  # your rewrite call
                    row.update({
                        "ethical": True,
                        "choice": j["choice"],
                        "principle": j["principle"],
                        "note": j["note"],
                        "rewrite": rw
                    })
                    ethical += 1

                outfile.write(json.dumps(row, ensure_ascii=False) + "\n")
                outfile.flush()
                seen.add(pid)
                done += 1

            except Exception as e:
                failed += 1
                errfile.write(json.dumps({
                    "error": str(e),
                    "line": line
                }, ensure_ascii=False) + "\n")
                errfile.flush()

            pbar.set_postfix(done=done, ethical=ethical, nonethical=nonethical, failed=failed, skipped=skipped)

        pbar.close()

if __name__ == "__main__":
    main()