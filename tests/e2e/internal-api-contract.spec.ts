import { spawn, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { expect, request as playwrightRequest, test, type APIRequestContext, type APIResponse } from "@playwright/test";
import { DEFAULT_AOI_ID, DEFAULT_PRIORITY_FEATURE_ID } from "./helpers/crisis-map";

// API tests start their own Next.js processes with different env modes. Keep
// service workers blocked for consistency with the network-routed UI specs.
test.use({ serviceWorkers: "block" });
test.describe.configure({ mode: "serial" });

const apiBasePath = "/api/internal/v1";
const endpointPaths = [
  "/catalog",
  "/aois",
  `/aois/${DEFAULT_AOI_ID}`,
  `/features?aoi_id=${DEFAULT_AOI_ID}&limit=5`,
  `/priority?aoi_id=${DEFAULT_AOI_ID}&limit=5`,
  `/search?q=${DEFAULT_PRIORITY_FEATURE_ID}&limit=10`,
  "/summary",
];

test("disabled internal API returns 403 for every public contract endpoint", async () => {
  const server = await startNextServer({
    INTERNAL_API_ENABLED: "false",
    INTERNAL_API_ALLOW_NO_TOKEN: "false",
    INTERNAL_API_TOKEN: "",
  });
  const api = await playwrightRequest.newContext({ baseURL: server.baseURL });

  try {
    for (const endpoint of endpointPaths) {
      const response = await api.get(`${apiBasePath}${endpoint}`);
      expect(response.status(), endpoint).toBe(403);
    }
  } finally {
    await api.dispose();
    await server.stop();
  }
});

test("enabled no-token mode returns sane response shapes", async () => {
  const server = await startNextServer({
    INTERNAL_API_ENABLED: "true",
    INTERNAL_API_ALLOW_NO_TOKEN: "true",
    INTERNAL_API_TOKEN: "",
  });
  const api = await playwrightRequest.newContext({ baseURL: server.baseURL });

  try {
    await expectInternalApiShapes(api);
  } finally {
    await api.dispose();
    await server.stop();
  }
});

test("token-required mode rejects missing and wrong tokens, then accepts the correct token", async () => {
  const token = "worker-c-e2e-token";
  const server = await startNextServer({
    INTERNAL_API_ENABLED: "true",
    INTERNAL_API_ALLOW_NO_TOKEN: "false",
    INTERNAL_API_TOKEN: token,
  });
  const unauthenticatedApi = await playwrightRequest.newContext({ baseURL: server.baseURL });
  const wrongTokenApi = await playwrightRequest.newContext({
    baseURL: server.baseURL,
    extraHTTPHeaders: { authorization: "Bearer wrong-token" },
  });
  const authenticatedApi = await playwrightRequest.newContext({
    baseURL: server.baseURL,
    extraHTTPHeaders: { authorization: `Bearer ${token}` },
  });

  try {
    const missing = await unauthenticatedApi.get(`${apiBasePath}/catalog`);
    expect([401, 403]).toContain(missing.status());

    const wrong = await wrongTokenApi.get(`${apiBasePath}/catalog`);
    expect([401, 403]).toContain(wrong.status());

    const accepted = await authenticatedApi.get(`${apiBasePath}/catalog`);
    expect(accepted.status()).toBe(200);
    await expectInternalApiShapes(authenticatedApi);
  } finally {
    await unauthenticatedApi.dispose();
    await wrongTokenApi.dispose();
    await authenticatedApi.dispose();
    await server.stop();
  }
});

async function expectInternalApiShapes(api: APIRequestContext) {
  const catalog = unwrapObject(await expectOkJson(await api.get(`${apiBasePath}/catalog`)));
  const catalogAois = collectionFrom(catalog, "aois");
  expect(catalog.updatedAt).toEqual(expect.any(String));
  expect(catalogAois.length).toBeGreaterThan(0);
  expect(catalogAois[0]).toEqual(expect.objectContaining({
    id: expect.any(String),
    name: expect.any(Object),
    status: expect.any(String),
    layers: expect.any(Object),
    metrics: expect.any(Object),
  }));

  const aois = collectionFrom(unwrapPayload(await expectOkJson(await api.get(`${apiBasePath}/aois`))), "aois");
  expect(aois.find((aoi) => aoi.id === DEFAULT_AOI_ID)).toEqual(expect.objectContaining({
    id: DEFAULT_AOI_ID,
    name: expect.any(Object),
    center: expect.any(Array),
    bounds: expect.any(Array),
    status: expect.any(String),
  }));

  const aoi = unwrapObject(await expectOkJson(await api.get(`${apiBasePath}/aois/${DEFAULT_AOI_ID}`)));
  expect(aoi).toEqual(expect.objectContaining({
    id: DEFAULT_AOI_ID,
    downloads: expect.any(Object),
    layers: expect.any(Object),
    metrics: expect.any(Object),
  }));

  const features = collectionFrom(
    unwrapPayload(await expectOkJson(await api.get(`${apiBasePath}/features?aoi_id=${DEFAULT_AOI_ID}&limit=5`))),
    "features",
  );
  expect(features.length).toBeGreaterThan(0);
  expect(features[0]).toEqual(expect.objectContaining({
    type: "Feature",
    geometry: expect.any(Object),
    properties: expect.objectContaining({
      id: expect.any(String),
      aoi_id: DEFAULT_AOI_ID,
    }),
  }));

  const priority = collectionFrom(
    unwrapPayload(await expectOkJson(await api.get(`${apiBasePath}/priority?aoi_id=${DEFAULT_AOI_ID}&limit=5`))),
    "priority",
  );
  expect(priority.length).toBeGreaterThan(0);
  expect(priority[0]).toEqual(expect.objectContaining({
    id: expect.any(String),
    aoi_id: DEFAULT_AOI_ID,
    google_maps_url: expect.stringMatching(/^https:\/\/www\.google\.com\/maps\/search\//),
  }));

  const search = collectionFrom(
    unwrapPayload(await expectOkJson(await api.get(`${apiBasePath}/search?q=${DEFAULT_PRIORITY_FEATURE_ID}&limit=10`))),
    "results",
  );
  expect(search.length).toBeGreaterThan(0);
  expect(search.some((result) => JSON.stringify(result).includes(DEFAULT_PRIORITY_FEATURE_ID))).toBe(true);
  expect(search[0]).toEqual(expect.objectContaining({
    id: expect.any(String),
    type: expect.any(String),
    label: expect.any(String),
  }));

  const summary = unwrapObject(await expectOkJson(await api.get(`${apiBasePath}/summary`)));
  expect(summary).toEqual(expect.objectContaining({
    updatedAt: expect.any(String),
  }));
  expect(Object.values(summary).some((value) => typeof value === "number" || Array.isArray(value) || isRecord(value))).toBe(true);
}

async function expectOkJson(response: APIResponse) {
  expect(response.status(), response.url()).toBe(200);
  expect(response.headers()["content-type"] ?? "", response.url()).toContain("application/json");
  return response.json() as Promise<unknown>;
}

function unwrapPayload(json: unknown): Record<string, unknown> | unknown[] {
  if (!isRecord(json)) throw new Error(`Expected JSON object payload, received ${typeof json}`);
  if ("data" in json) {
    const data = json.data;
    if (isRecord(data) || Array.isArray(data)) return data;
  }
  return json;
}

function unwrapObject(json: unknown): Record<string, unknown> {
  const payload = unwrapPayload(json);
  if (!isRecord(payload)) throw new Error("Expected JSON object payload");
  return payload;
}

function collectionFrom(payload: Record<string, unknown> | unknown[], preferredKey: string) {
  if (Array.isArray(payload)) return payload as Array<Record<string, unknown>>;
  if (Array.isArray(payload[preferredKey])) return payload[preferredKey] as Array<Record<string, unknown>>;
  if (Array.isArray(payload.items)) return payload.items as Array<Record<string, unknown>>;
  if (Array.isArray(payload.results)) return payload.results as Array<Record<string, unknown>>;
  if (payload.type === "FeatureCollection" && Array.isArray(payload.features)) {
    return payload.features as Array<Record<string, unknown>>;
  }
  throw new Error(`Expected collection under ${preferredKey}, items, results, or FeatureCollection.features`);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function startNextServer(env: Record<string, string>) {
  const port = await findOpenPort();
  const child = spawn("npm", ["run", "start", "--", "-p", String(port)], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      ...env,
      PLAYWRIGHT_PORT: String(port),
      PORT: String(port),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const logs: string[] = [];
  child.stdout.on("data", (chunk) => logs.push(String(chunk)));
  child.stderr.on("data", (chunk) => logs.push(String(chunk)));

  try {
    await waitForServer(`http://127.0.0.1:${port}`, child, logs);
  } catch (error) {
    child.kill();
    throw error;
  }

  return {
    baseURL: `http://127.0.0.1:${port}`,
    stop: async () => {
      if (child.exitCode !== null) return;
      child.kill();
      await Promise.race([
        new Promise((resolve) => child.once("exit", resolve)),
        new Promise((resolve) => setTimeout(resolve, 5_000)),
      ]);
    },
  };
}

async function waitForServer(baseURL: string, child: ChildProcess, logs: string[]) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 120_000) {
    if (child.exitCode !== null) {
      throw new Error(`Next server exited before ready.\n${logs.join("")}`);
    }
    try {
      const response = await fetch(baseURL);
      if (response.status < 500) return;
    } catch {
      // Retry until next start binds the port.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for Next server.\n${logs.join("")}`);
}

async function findOpenPort() {
  return new Promise<number>((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        reject(new Error("Unable to allocate a local port"));
        return;
      }
      server.close(() => resolve(address.port));
    });
  });
}
