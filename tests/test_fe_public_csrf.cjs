"use strict";
const assert=require("assert"), fs=require("fs");
const source=fs.readFileSync("persona/api/static/index.html","utf8");
assert(source.includes("/api/auth/session"),"public UI obtains a session CSRF token");
assert(source.includes("X-CSRF-Token"),"public UI attaches CSRF token to unsafe API requests");
assert(source.includes("url.startsWith('/api/')"),"token injection is scoped to Persona API requests");
console.log("OK — public CSRF wiring present");
