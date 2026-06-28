import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const outDir = new URL("./", import.meta.url).pathname;
const baseUrl = process.env.QA_BASE_URL || "http://127.0.0.1:4695";
const findings = [];
const passes = [];
const screenshots = [];
const browserCandidates = [
  process.env.PLAYWRIGHT_CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
].filter(Boolean);

function ok(name, detail = "") {
  passes.push({ name, detail });
}

function fail(name, detail, screenshot) {
  findings.push({ name, detail, screenshot });
}

async function shot(page, name) {
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: false });
  screenshots.push(file);
  return file;
}

async function debug(page) {
  return page.evaluate(() => {
    const node = document.querySelector(".map-node");
    return {
      mapDebug: window.__damageMapDebug,
      selectedId: node?.getAttribute("data-selected-id") || "",
      focusedId: node?.getAttribute("data-focused-id") || "",
      visibleCount: Number(node?.getAttribute("data-visible-features") || 0),
      zoomAttr: Number(node?.getAttribute("data-map-zoom") || 0),
      mode: node?.getAttribute("data-mode") || "",
      filter: node?.getAttribute("data-filter") || "",
      basemap: node?.getAttribute("data-basemap") || "",
      opacity: Number(node?.getAttribute("data-opacity") || 0),
      popupText: document.querySelector(".ol-popup")?.textContent?.trim() || "",
      activeCity: document.querySelector(".aoi-card.active span")?.textContent?.trim() || "",
      downloads: [...document.querySelectorAll(".downloads-section a")].map((a) => ({
        text: a.textContent?.trim(),
        href: a.getAttribute("href"),
      })),
      beforeDisabled: document.querySelector("[data-testid='mode-before']")?.disabled ?? null,
      afterDisabled: document.querySelector("[data-testid='mode-after']")?.disabled ?? null,
      beforeActive: document.querySelector("[data-testid='mode-before']")?.classList.contains("active") ?? false,
      afterActive: document.querySelector("[data-testid='mode-after']")?.classList.contains("active") ?? false,
    };
  });
}

async function waitForFeatures(page, expectedMin = 1) {
  await page.waitForFunction((min) => window.__damageMapDebug?.visibleFeatures?.length >= min, expectedMin, { timeout: 20000 });
}

async function waitSettled(page) {
  await page.waitForTimeout(800);
}

async function validateDownloadLinks(page, label) {
  const links = await debug(page).then((d) => d.downloads);
  const bad = [];
  for (const link of links) {
    if (!link.href) {
      bad.push(`${link.text}: missing href`);
      continue;
    }
    if (link.href.startsWith("http")) continue;
    const res = await page.request.get(new URL(link.href, baseUrl).toString());
    if (!res.ok()) bad.push(`${link.text}: ${res.status()} ${link.href}`);
  }
  if (bad.length) fail(`${label}: downloads`, bad.join("; "));
  else ok(`${label}: downloads`, links.map((l) => `${l.text}=${l.href}`).join(", "));
}

async function checkAoiIsolation(page, expectedAoi, label) {
  const ids = await page.evaluate(() => window.__damageMapDebug?.visibleFeatures ?? []);
  const leaked = ids.filter((id) => !String(id).startsWith(`${expectedAoi}__`));
  if (leaked.length) fail(`${label}: AOI isolation`, `Leaked non-active AOI features: ${leaked.slice(0, 5).join(", ")}`);
  else ok(`${label}: AOI isolation`, `${ids.length} visible features all belong to ${expectedAoi}`);
}

async function runViewport(browser, viewport, label) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") findings.push({ name: `${label}: console error`, detail: msg.text() });
  });
  page.on("response", (response) => {
    if (response.status() === 401) findings.push({ name: `${label}: HTTP 401`, detail: response.url() });
  });
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
  await waitForFeatures(page, 1);
  await waitSettled(page);
  await shot(page, `${label}-01-default-aoi12.png`);

  let d = await debug(page);
  if (d.activeCity.includes("La Guaira") && d.visibleCount === 120) ok(`${label}: default AOI selector`, "La Guaira active with 120 AOI12 features");
  else fail(`${label}: default AOI selector`, `activeCity=${d.activeCity}, visibleCount=${d.visibleCount}`, await shot(page, `${label}-fail-default-aoi.png`));
  await checkAoiIsolation(page, "emsr884-aoi12-caraballeda", `${label}: default`);
  await validateDownloadLinks(page, `${label}: AOI12`);

  await page.getByTestId("mode-before").click();
  await waitSettled(page);
  d = await debug(page);
  if (d.mode === "before" && d.mapDebug?.raster === "before" && d.beforeActive) ok(`${label}: AOI12 Vantor before`, "before raster active");
  else fail(`${label}: AOI12 Vantor before`, JSON.stringify(d), await shot(page, `${label}-fail-aoi12-before.png`));
  await shot(page, `${label}-02-aoi12-vantor-before.png`);
  await page.getByTestId("mode-after").click();
  await waitSettled(page);
  d = await debug(page);
  if (d.mode === "after" && d.mapDebug?.raster === "after" && d.afterActive) ok(`${label}: AOI12 after`, "after raster active");
  else fail(`${label}: AOI12 after`, JSON.stringify(d), await shot(page, `${label}-fail-aoi12-after.png`));

  const allCount = d.visibleCount;
  await page.getByTestId("filter-severe").click();
  await waitSettled(page);
  d = await debug(page);
  if (d.filter === "severe" && d.visibleCount <= allCount) ok(`${label}: severe filter`, `${d.visibleCount}/${allCount}`);
  else fail(`${label}: severe filter`, JSON.stringify(d));
  await page.getByTestId("filter-vlm").click();
  await waitSettled(page);
  d = await debug(page);
  if (d.filter === "vlm" && d.visibleCount <= allCount) ok(`${label}: VLM filter`, `${d.visibleCount}/${allCount}`);
  else fail(`${label}: VLM filter`, JSON.stringify(d));
  await page.getByTestId("filter-all").click();
  await waitSettled(page);
  d = await debug(page);
  if (d.filter === "all" && d.visibleCount === allCount) ok(`${label}: all filter restore`, `${d.visibleCount}`);
  else fail(`${label}: all filter restore`, JSON.stringify(d));

  const zoomBeforeOpacity = d.mapDebug?.zoom;
  await page.getByRole("button", { name: "increase damage opacity" }).click();
  await waitSettled(page);
  d = await debug(page);
  if (Math.abs(d.opacity - 0.62) < 0.001 && Math.abs((d.mapDebug?.zoom ?? 0) - zoomBeforeOpacity) < 0.001) ok(`${label}: opacity`, `opacity=${d.opacity}, zoom unchanged=${d.mapDebug?.zoom}`);
  else fail(`${label}: opacity`, `beforeZoom=${zoomBeforeOpacity}, after=${JSON.stringify(d)}`, await shot(page, `${label}-fail-opacity.png`));

  await page.locator(".priority-row").first().click();
  await waitSettled(page);
  d = await debug(page);
  if (d.focusedId && d.popupText && Math.round(d.zoomAttr || d.mapDebug?.zoom || 0) === 18) ok(`${label}: priority click zoom/popup`, `focused=${d.focusedId}, zoom=${d.zoomAttr || d.mapDebug?.zoom}`);
  else fail(`${label}: priority click zoom/popup`, JSON.stringify(d), await shot(page, `${label}-fail-priority-popup.png`));
  await shot(page, `${label}-03-priority-popup.png`);

  const mapBox = await page.locator(".map-node").boundingBox();
  if (!mapBox) throw new Error("Map node has no bounding box");
  const clearCandidates = [
    [0.08, 0.08],
    [0.92, 0.08],
    [0.08, 0.42],
    [0.92, 0.42],
    [0.50, 0.20],
    [0.50, 0.50],
  ];
  for (const [xRatio, yRatio] of clearCandidates) {
    await page.mouse.click(mapBox.x + mapBox.width * xRatio, mapBox.y + mapBox.height * yRatio);
    await waitSettled(page);
    d = await debug(page);
    if (!d.selectedId && !d.focusedId && !d.popupText) break;
  }
  if (!d.selectedId && !d.focusedId && !d.popupText) ok(`${label}: click outside clears popup`, "selection cleared");
  else fail(`${label}: click outside clears popup`, JSON.stringify(d), await shot(page, `${label}-fail-clear-popup.png`));

  await page.getByTestId("city-antimano").click();
  await waitSettled(page);
  d = await debug(page);
  if (d.activeCity.includes("Ant") && d.visibleCount === 0) ok(`${label}: AOI selector Antimano`, "imagery-only AOI active with no features");
  else fail(`${label}: AOI selector Antimano`, JSON.stringify(d), await shot(page, `${label}-fail-antimano-selector.png`));
  await checkAoiIsolation(page, "emsr884-aoi03-antimano", `${label}: Antimano`);
  await page.getByTestId("mode-before").click();
  await waitSettled(page);
  d = await debug(page);
  if (d.mode === "before" && d.mapDebug?.raster === "before" && !d.beforeDisabled) ok(`${label}: Esri approximate before fallback`, "before uses approximate raster");
  else fail(`${label}: Esri approximate before fallback`, JSON.stringify(d), await shot(page, `${label}-fail-esri-before.png`));
  await shot(page, `${label}-04-antimano-esri-before.png`);

  await validateDownloadLinks(page, `${label}: Antimano`);
  await context.close();
}

await fs.mkdir(outDir, { recursive: true });
let executablePath;
for (const candidate of browserCandidates) {
  try {
    await fs.access(candidate);
    executablePath = candidate;
    break;
  } catch {
    // Continue to bundled Playwright browser if no system browser is present.
  }
}

const browser = await chromium.launch(executablePath ? { executablePath } : {});
try {
  await runViewport(browser, { width: 1440, height: 950 }, "desktop");
  await runViewport(browser, { width: 390, height: 844 }, "mobile");
} finally {
  await browser.close();
}

const report = [
  "# Crisis Damage Intelligence Operational QA",
  "",
  `Base URL: ${baseUrl}`,
  `Generated: ${new Date().toISOString()}`,
  "",
  "## Result",
  "",
  findings.length ? `FAIL - ${findings.length} finding(s)` : "PASS - no functional failures found in requested scope",
  "",
  "## Passes",
  "",
  ...passes.map((p) => `- ${p.name}${p.detail ? `: ${p.detail}` : ""}`),
  "",
  "## Findings",
  "",
  ...(findings.length ? findings.map((f) => `- ${f.name}: ${f.detail}${f.screenshot ? ` (${path.basename(f.screenshot)})` : ""}`) : ["- None"]),
  "",
  "## Screenshots",
  "",
  ...screenshots.map((file) => `- ${path.basename(file)}`),
  "",
].join("\n");

await fs.writeFile(path.join(outDir, "operational_qa_report.md"), report);
console.log(report);
