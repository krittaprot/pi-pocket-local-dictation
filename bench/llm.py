# Cleanup experiment: how much does an LLM lower the error rate of two recognizers' output?
# Needs out-A.json and out-B.json from bench.py (rename its out-<port>.json files), and LLM_URL / LLM_MODEL / LLM_KEY.
import json, re, unicodedata, urllib.request, concurrent.futures as cf, os, sys
key = os.environ.get("LLM_KEY","")
A = {r["f"]: r for r in json.load(open("out-A.json"))}   # thonburian
B = {r["f"]: r for r in json.load(open("out-B.json"))}   # typhoon
def norm(s): return re.sub(r"[\s\W_]+", "", unicodedata.normalize("NFC", s.lower()))
def lev(a, b):
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1): cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(ca != cb)))
        prev = cur
    return prev[-1]
SYS_ONE = "You fix speech-to-text errors in Thai. Output only the corrected Thai transcript. Keep the speaker's words; fix misheard words, spelling, tone marks and wrongly split or merged words. Never translate."
SYS_TWO = "You get two speech-to-text transcripts of the same Thai audio from two different recognizers. Output only the single best Thai transcript: where they differ, choose or combine what is most plausible Thai. Keep the speaker's words; never translate, add, or summarize."
def ask(system, user):
    d = json.dumps({"model": os.environ.get("LLM_MODEL","local-model"), "messages": [{"role":"system","content":system},{"role":"user","content":user}], "max_tokens": 3000, "reasoning_effort": os.environ.get("RE","low")}).encode()
    r = urllib.request.Request(""+os.environ.get("LLM_URL","http://127.0.0.1:1234/v1")+"/chat/completions", data=d, headers={"Authorization": f"Bearer {key}", "content-type": "application/json", "User-Agent": "curl/8.7"})
    return ((json.load(urllib.request.urlopen(r, timeout=90))["choices"][0]["message"]["content"]) or "").strip()
files = list(A)
def cer(h): 
    e = sum(lev(norm(h[f]), norm(A[f]["ref"])) for f in files); c = sum(len(norm(A[f]["ref"])) for f in files); return e/c
def run(fn):
    with cf.ThreadPoolExecutor(4) as ex: return dict(zip(files, ex.map(fn, files)))
print("thonburian raw ", round(cer({f: A[f]["hyp"] for f in files}),3))
print("typhoon raw    ", round(cer({f: B[f]["hyp"] for f in files}),3))
one = run(lambda f: ask(SYS_ONE, f"<<<\n{A[f]['hyp']}\n>>>") or A[f]["hyp"])
print("thon + LLM fix ", round(cer(one),3))
two = run(lambda f: ask(SYS_TWO, f"Transcript 1:\n{A[f]['hyp']}\n\nTranscript 2:\n{B[f]['hyp']}") or A[f]["hyp"])
print("thon+typh+LLM  ", round(cer(two),3))
json.dump({"one": one, "two": two}, open("llm-out.json","w"), ensure_ascii=False, indent=1)
