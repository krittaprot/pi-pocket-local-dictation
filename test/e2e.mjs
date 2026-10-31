// End to end: audio -> whisper.cpp -> (final pass) -> cleanup LLM, scored against reference text.
// SETTINGS='{"liveModel":"...","finalModels":"thai=...","cleanupUrl":"http://127.0.0.1:8080/v1"}' \
//   node test/e2e.mjs <folder with *.pcm (16 kHz mono s16le)> <refs.tsv: id<TAB>file<TAB>text> [clips]
import fs from "node:fs";
import { load } from "./harness.mjs";

const [dir, refsFile, count = "10"] = process.argv.slice(2);
const { routes, call } = await load(JSON.parse(process.env.SETTINGS ?? "{}"));
const refs = {};

for (const line of fs.readFileSync(refsFile, "utf8").split("\n")) {
    const part = line.split("\t");

    if (part[1] && !refs[part[1]]) {
        refs[part[1]] = part[2];
    }
}

const norm = (text) => text.toLowerCase().replace(/[\s\p{P}\p{S}_]+/gu, "");
const lev = (a, b) => {
    let prev = [...Array(b.length + 1).keys()];

    for (let i = 1; i <= a.length; i++) {
        const cur = [i];

        for (let j = 1; j <= b.length; j++) {
            cur.push(Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] !== b[j - 1] ? 1 : 0)));
        }

        prev = cur;
    }

    return prev[b.length];
};

await call("warm", {});

const files = fs.readdirSync(dir).filter((file) => file.endsWith(".pcm")).slice(0, Number(count));
let rawErrors = 0, fixedErrors = 0, chars = 0, delay = 0;

for (const file of files) {
    const pcm = fs.readFileSync(`${dir}/${file}`);
    const id = `e2e-${file.slice(0, 12)}`;
    const ref = norm(refs[file.replace(".pcm", ".wav")] ?? "");

    for (let at = 0; at < pcm.length; at += 32000) {
        await call("push", { id, pcm: pcm.subarray(at, at + 32000).toString("base64"), last: false });
        await new Promise((done) => setTimeout(done, 400));
    }

    const t = Date.now();
    const result = await call("push", { id, last: true, context: { recent: [], draft: "", where: "test" } });

    delay += Date.now() - t;
    rawErrors += lev(norm(result.raw), ref);
    fixedErrors += lev(norm(result.text), ref);
    chars += ref.length;
}

console.log(`clips=${files.length} rawCER=${(rawErrors / chars).toFixed(3)} fixedCER=${(fixedErrors / chars).toFixed(3)} avgStopDelay=${(delay / files.length / 1000).toFixed(1)}s`);
routes.dispose();
process.exit(0);
