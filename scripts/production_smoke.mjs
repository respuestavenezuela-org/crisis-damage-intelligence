#!/usr/bin/env node

const defaultAoiId = "emsr884-aoi12-caraballeda";

const args = parseArgs(process.argv.slice(2));
const baseUrl = normalizeBaseUrl(args.baseUrl ?? args._[0]);
const timeoutMs = Number(args.timeoutMs ?? 15_000);
const defaultAoi = args.defaultAoi ?? defaultAoiId;
const apiEnabled = Boolean(args.apiEnabled);
const expectApiDisabled = Boolean(args.expectApiDisabled);

if (!baseUrl) {
  console.error("Usage: node scripts/production_smoke.mjs --base-url https://respuestavenezuela.org [--api-enabled] [--api-token token]");
  process.exit(2);
}

const failures = [];

await check("home page", async () => {
  const { response, text } = await fetchText("/");
  expectStatus(response, 200);
  expectHeader(response, "content-type", /text\/html/i);
  expectMatch(text, /Respuesta Venezuela|Loading crisis map/i, "home page should contain the app shell");
});

await check("web app manifest", async () => {
  const { response, json } = await fetchJson("/manifest.webmanifest");
  expectStatus(response, 200);
  expectHeader(response, "content-type", /json|manifest/i);
  expectTruthy(json.name || json.short_name, "manifest should expose a name or short_name");
});

await check("service worker", async () => {
  const { response, text } = await fetchText("/sw.js");
  expectStatus(response, 200);
  expectHeader(response, "content-type", /javascript|ecmascript|text\/plain/i);
  expectMatch(text, /self\.|addEventListener|workbox|cache/i, "service worker should look like executable JS");
});

let catalog;
await check("catalog", async () => {
  const result = await fetchJson("/data/catalog.json");
  expectStatus(result.response, 200);
  expectHeader(result.response, "content-type", /json/i);
  catalog = result.json;
  expectTruthy(Array.isArray(catalog.aois), "catalog.aois should be an array");
  expectTruthy(catalog.aois.some((aoi) => aoi.id === defaultAoi), `catalog should include ${defaultAoi}`);
});

await check("default AOI damage data", async () => {
  const aoi = catalog?.aois?.find((candidate) => candidate.id === defaultAoi);
  expectTruthy(aoi, `missing default AOI ${defaultAoi}`);
  expectTruthy(aoi.layers?.damage, `${defaultAoi} should expose layers.damage`);
  const result = await fetchJson(aoi.layers.damage);
  expectStatus(result.response, 200);
  expectHeader(result.response, "content-type", /json|geojson/i);
  expectTruthy(result.json.type === "FeatureCollection", "damage layer should be a FeatureCollection");
  expectTruthy(Array.isArray(result.json.features), "damage layer should expose features");
});

if (apiEnabled) {
  await check("internal API health", async () => {
    const headers = args.apiToken ? { authorization: `Bearer ${args.apiToken}` } : {};
    const result = await fetchJson("/api/internal/v1/health", { headers });
    expectStatus(result.response, 200);
    expectHeader(result.response, "content-type", /json/i);
    expectTruthy(result.json.ok !== false, "health response should not report ok=false");
  });
} else if (expectApiDisabled) {
  await check("internal API disabled health", async () => {
    const response = await fetchWithTimeout("/api/internal/v1/health");
    expectStatus(response, 403);
  });
}

if (failures.length) {
  console.error(`\nProduction smoke failed for ${baseUrl}`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Production smoke passed for ${baseUrl}`);

async function check(label, fn) {
  try {
    await fn();
    console.log(`ok - ${label}`);
  } catch (error) {
    failures.push(`${label}: ${error instanceof Error ? error.message : String(error)}`);
    console.error(`not ok - ${label}`);
  }
}

async function fetchText(pathOrUrl, init = {}) {
  const response = await fetchWithTimeout(pathOrUrl, init);
  return { response, text: await response.text() };
}

async function fetchJson(pathOrUrl, init = {}) {
  const response = await fetchWithTimeout(pathOrUrl, init);
  const text = await response.text();
  try {
    return { response, json: JSON.parse(text) };
  } catch (error) {
    throw new Error(`invalid JSON from ${pathOrUrl}: ${error instanceof Error ? error.message : String(error)}`);
  }
}

async function fetchWithTimeout(pathOrUrl, init = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(new URL(pathOrUrl, baseUrl), {
      redirect: "follow",
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

function expectStatus(response, status) {
  if (response.status !== status) throw new Error(`expected HTTP ${status}, received ${response.status} for ${response.url}`);
}

function expectHeader(response, name, pattern) {
  const value = response.headers.get(name) ?? "";
  if (!pattern.test(value)) throw new Error(`expected ${name} to match ${pattern}, received "${value}"`);
}

function expectTruthy(value, message) {
  if (!value) throw new Error(message);
}

function expectMatch(value, pattern, message) {
  if (!pattern.test(value)) throw new Error(message);
}

function normalizeBaseUrl(value) {
  if (!value) return "";
  const withProtocol = /^https?:\/\//i.test(value) ? value : `https://${value}`;
  return withProtocol.endsWith("/") ? withProtocol : `${withProtocol}/`;
}

function parseArgs(argv) {
  const parsed = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) {
      parsed._.push(arg);
      continue;
    }
    const key = arg.slice(2).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
    } else {
      parsed[key] = next;
      i += 1;
    }
  }
  return parsed;
}
