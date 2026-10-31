// Loads local-dictation.ts with a stand-in `web`, so its routes can be called without Pi Pocket.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

/** A copy of the module in a temp folder with a stand-in for the one package Pi Pocket provides, so it loads on its own. */
function stage() {
    const dir = path.join(os.tmpdir(), "local-dictation-test");
    const pkg = path.join(dir, "node_modules/@earendil-works/pi-durable");

    fs.mkdirSync(pkg, { recursive: true });
    fs.writeFileSync(path.join(pkg, "package.json"), '{"name":"@earendil-works/pi-durable","type":"module","main":"index.js"}');
    fs.writeFileSync(path.join(pkg, "index.js"), "export const defineExtension = (extension) => extension;\n");
    fs.copyFileSync(fileURLToPath(new URL("../local-dictation.ts", import.meta.url)), path.join(dir, "local-dictation.ts"));

    return pathToFileURL(path.join(dir, "local-dictation.ts")).href + `?${Date.now()}`;
}

export async function load(settings = {}) {
    const mod = await import(stage());
    const routes = {};
    const declared = [];
    const web = {
        settings: (fields) => declared.push(...fields),
        setting: (name) => settings[name] ?? declared.find((field) => field.name === name)?.default,
        route: (method, path, handle, options) => (routes[path] = { method, handle, options }),
        client: (entry) => (routes.client = entry),
        onDispose: (dispose) => (routes.dispose = dispose),
        error: (status, message) => Object.assign(new Error(message), { status }),
    };
    const extension = mod.default({}, web);

    return { extension, routes, declared, call: (path, body) => routes[path].handle({ body, signal: new AbortController().signal }) };
}
