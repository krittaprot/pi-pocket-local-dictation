import sys, os, json, time, re, urllib.request, subprocess, uuid, unicodedata
# Measures a whisper-server's character error rate on FLEURS clips.
# Run it in a folder that has fleurs/*.wav (16 kHz) and test.tsv (from google/fleurs, th_th/test.tsv, or another language).
# usage: python3 -I bench.py <port> <number of clips> [form field=value ...]   e.g. language=th
port, n = sys.argv[1], int(sys.argv[2]); extra = dict(a.split("=",1) for a in sys.argv[3:])
refs = {}
for line in open("test.tsv", encoding="utf8"):
    p = line.rstrip("\n").split("\t")
    if len(p) > 3 and p[1] not in refs: refs[p[1]] = p[2]
files = sorted(f for f in os.listdir("fleurs") if f in refs)[:n]
def norm(s): return re.sub(r"[\s\W_]+", "", unicodedata.normalize("NFC", s.lower()))
def lev(a, b):
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(ca != cb)))
        prev = cur
    return prev[-1]
def post(path, fields):
    b = uuid.uuid4().hex; body = b""
    for k, v in fields.items():
        if k == "file":
            body += f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode() + v + b"\r\n"
        else:
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += f"--{b}--\r\n".encode()
    r = urllib.request.Request(f"http://127.0.0.1:{port}/inference", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.load(urllib.request.urlopen(r, timeout=120))["text"].strip()
errs = chars = 0; t0 = time.time(); out = []
for f in files:
    wav = open(f"fleurs/{f}", "rb").read()
    hyp = post("", {"file": wav, "response_format": "json", "temperature": "0.0", **extra})
    ref = refs[f]; e = lev(norm(hyp), norm(ref)); errs += e; chars += len(norm(ref))
    out.append({"f": f, "ref": ref, "hyp": hyp})
json.dump(out, open(f"out-{port}.json", "w"), ensure_ascii=False, indent=1)
print(f"files={len(files)} CER={errs/chars:.3f} time={time.time()-t0:.0f}s")
