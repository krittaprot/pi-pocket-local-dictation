// Offline check: the module loads, declares its settings and routes, and a missing model is a clear error.
import assert from "node:assert/strict";
import { load } from "./harness.mjs";

const { extension, routes, declared, call } = await load({ liveModel: "/nonexistent.bin" });

assert.equal(extension.name, "local-dictation");
assert.equal(routes.client, "local-dictation");
assert.deepEqual(Object.keys(routes).filter((key) => routes[key].method === "POST").sort(), ["push", "warm"]);
assert.ok(declared.some((field) => field.name === "cleanupUrl"));
assert.equal(declared.find((field) => field.name === "cleanupKey").secret, true);
assert.equal((await call("push", { id: "bad id" }).catch((error) => error)).status, 400);
assert.deepEqual(await call("push", { id: "take-drop-1", drop: true }), {});
routes.dispose();
console.log("smoke ok");
