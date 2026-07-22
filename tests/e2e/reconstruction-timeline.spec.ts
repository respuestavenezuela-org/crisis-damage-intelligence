import { expect, test } from "@playwright/test";

test.describe("public aftermath reconstruction", () => {
  test("explains the first 72 hours and preserves source traceability", async ({ page }) => {
    const loadedHeavyData: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      if (/\/data\/(?:aoi|tiles)\//.test(url) || /\.(?:geojson|jsonl|pmtiles|tif)$/i.test(url)) {
        loadedHeavyData.push(url);
      }
    });

    await page.goto("/timeline");

    await expect(page.getByRole("heading", { name: "Lo que pasó después" })).toBeVisible();
    await expect(page.getByText("¿Cuándo llegó la ayuda — y cuándo llegó realmente a los sitios?")).toBeVisible();
    await expect(page.getByText(/La ayuda se movilizó pronto/)).toBeVisible();
    await expect(page.getByText("Observado en sitio").first()).toBeVisible();
    await expect(page.getByRole("img", { name: /Comparación antes y después/ }).first()).toBeVisible();

    const sourceLinks = page.locator('a[target="_blank"]');
    await expect(sourceLinks.first()).toHaveAttribute("href", /^https:\/\//);
    expect(loadedHeavyData).toEqual([]);

    await page.getByRole("button", { name: "Después de 72 h" }).click();
    await expect(page.getByRole("button", { name: "Después de 72 h" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator('article[id^="event-"]')).toHaveCount(12);

    await page.getByRole("button", { name: "EN", exact: true }).click();
    await expect(page.getByRole("heading", { name: "What happened after" })).toBeVisible();
    await expect(page.getByText("Not observed ≠ did not happen")).toBeVisible();
  });

  test("has no horizontal overflow on a small phone", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/timeline");

    await expect(page.getByRole("heading", { name: "Lo que pasó después" })).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);

    const mapLink = page.getByRole("link", { name: "Abrir mapa de daños" });
    const box = await mapLink.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  });

  test("publishes the audited aerial response review without promoting model detections", async ({ page }) => {
    await page.goto("/timeline");

    const section = page.locator("#aerial-evidence");
    await expect(section.getByRole("heading", { name: "¿Qué respuesta puede verse desde arriba?" })).toBeVisible();
    await expect(section.getByText("734", { exact: true })).toBeVisible();
    await expect(section.locator("figure")).toHaveCount(10);
    await expect(section.getByText(/cuatro nuevos sitios temporales compatibles con respuesta/)).toBeVisible();
    await expect(section.getByText(/sin superresolución/)).toBeVisible();
    await expect(section.getByText("Inventario oficial de adquisiciones")).toBeVisible();
    await expect(section.getByText("Adquisiciones ópticas distintas")).toBeVisible();
    await expect(section.getByText("21", { exact: true })).toBeVisible();

    await section.getByRole("button", { name: "Maquinaria", exact: true }).click();
    await expect(section.locator("figure")).toHaveCount(2);
    await section.getByRole("button", { name: "Probable respuesta", exact: true }).click();
    await expect(section.locator("figure")).toHaveCount(1);

    await section.getByRole("button", { name: "Vista mejorada 2×", exact: true }).click();
    await expect(section.getByText(/La mejora no crea detalle real/)).toBeVisible();
    await expect(section.locator("figure img")).toHaveAttribute(
      "src",
      /\/data\/reconstruction\/evidence\/la-guaira\/ems_00119_after_event_swin2sr_x2\.webp$/,
    );
    await expect(section.getByText("Derivada · solo visualización")).toBeVisible();

    await section.getByRole("button", { name: "Cambio fechado", exact: true }).click();
    await expect(section.getByText("Lectura del seguimiento")).toBeVisible();
    await expect(section.locator("figure img")).toHaveAttribute(
      "src",
      /\/data\/reconstruction\/evidence\/la-guaira\/temporal\/ems_00119_B140001100B5C710_compare\.png$/,
    );

    await section.getByRole("button", { name: "Seguimiento 2×", exact: true }).click();
    await expect(section.locator("figure img")).toHaveAttribute(
      "src",
      /\/data\/reconstruction\/evidence\/la-guaira\/temporal\/ems_00119_B140001100B5C710_swin2sr_x2\.webp$/,
    );
  });

  test("renders the full-pilot AI triage package with documentary traceability", async ({ page }) => {
    await page.route(
      "**/data/reconstruction/full-pilot-response-evidence-summary.json",
      async (route) => {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
            updatedAt: "2026-07-21T00:00:00Z",
            status: "public-ai-triage",
            coverage: {
              gridCells: 2283,
              eligibleImageryStacks: 2283,
              pairedVlmCoverage: 2283,
              postEventOnlyCells: 191,
              candidateCells: 412,
              withinFirst72Hours: 260,
              waldo30Cells: 2283,
              cropPairs: 500,
              nativeCropImages: 1000,
              enhancedDisplayImages: 200,
            },
            evidenceTierCounts: { cross_model_positive: 12 },
            timelineEvents: [
              {
                acquisitionUtc: "2026-06-26T15:10:00Z",
                hoursAfterEvent: 41.09,
                candidateCells: 30,
                bothModelsPositive: 12,
                detectorSupported: 4,
              },
            ],
            topObservations: [
              {
                cellId: "pilot_r010_c010",
                longitude: -66.95,
                latitude: 10.6,
                firstVisibleAcquisitionUtc: "2026-06-26T15:10:00Z",
                hoursAfterEvent: 41.09,
                evidenceTier: "cross_model_positive",
                consensus: "both_positive",
                priorityScore: 145,
                assetCategories: ["heavy_machinery"],
                evidencePair: null,
              },
            ],
            documentaryEvidence: {
              conflictsAndBounds: [
                {
                  topic: "Aid arrival",
                  topicEs: "Llegada de ayuda",
                  finding: "Aid trucks were observed by June 26.",
                  findingEs: "Se observaron camiones de ayuda para el 26 de junio.",
                  interpretation: "This does not establish delivery to every neighborhood.",
                  interpretationEs: "Esto no demuestra entrega en todos los sectores.",
                },
              ],
              sources: [
                {
                  id: "source-1",
                  publisher: "World Food Programme",
                  sourceType: "primary humanitarian agency update",
                  publishedAt: "2026-06-26",
                  url: "https://example.org/source",
                  places: ["La Guaira"],
                  claims: ["Temporary distribution centers were reported."],
                  claimsEs: ["Se reportaron centros temporales de distribución."],
                  timePrecision: "published June 26",
                  limitations: "No exact opening time",
                },
              ],
            },
            downloads: {
              candidateGeoJson: "/data/reconstruction/full-pilot-response-evidence.geojson",
              candidateJsonl: "/data/reconstruction/full-pilot-response-evidence.jsonl",
              cropManifest:
                "/data/reconstruction/full-pilot-response-evidence-crops.jsonl",
            },
            guardrails: ["AI triage only"],
          }),
        });
      },
    );

    await page.goto("/timeline");

    const section = page.locator("#full-pilot-evidence");
    await expect(
      section.getByRole("heading", {
        name: "2.283 celdas entre Catia La Mar, La Guaira y Caraballeda",
      }),
    ).toBeVisible();
    await expect(section.getByText("2.283", { exact: true }).first()).toBeVisible();
    await expect(section.getByText("Llegada de ayuda")).toBeVisible();
    await expect(section.getByText("Se reportaron centros temporales de distribución.")).toBeHidden();
    await section.getByText("World Food Programme").click();
    await expect(section.getByText("Se reportaron centros temporales de distribución.")).toBeVisible();
    await expect(section.getByRole("link", { name: /GeoJSON de candidatas/ })).toHaveAttribute(
      "href",
      "/data/reconstruction/full-pilot-response-evidence.geojson",
    );
  });

  test("is discoverable from lite view", async ({ page }) => {
    await page.goto("/lite");
    await expect(page.getByRole("link", { name: "Cronología" })).toHaveAttribute("href", "/timeline");
  });

  test("switches to the Morón evidence packet without loading map data", async ({ page }) => {
    const loadedHeavyData: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      if (/\/data\/(?:aoi|tiles)\//.test(url) || /\.(?:geojson|jsonl|pmtiles|tif)$/i.test(url)) {
        loadedHeavyData.push(url);
      }
    });

    await page.goto("/timeline/moron");

    await expect(page.getByRole("link", { name: /Morón y municipio Juan José Mora/ })).toHaveAttribute("aria-current", "page");
    await expect(page.getByText("Morón y municipio Juan José Mora, Carabobo").last()).toBeVisible();
    await expect(page.getByText(/su respuesta en Morón y municipio Juan José Mora/)).toBeVisible();
    await expect(page.getByText(/El daño fue cartografiado dentro de las primeras 24 horas/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Copernicus adquiere imagen postevento de Morón" })).toBeVisible();
    await expect(page.getByRole("img", { name: /elemento destruido en Morón/ }).first()).toBeVisible();
    await expect(page.getByText("Maquinaria pesada: hora de llegada no resuelta")).toBeVisible();
    expect(loadedHeavyData).toEqual([]);

    await page.getByRole("button", { name: "EN", exact: true }).click();
    await expect(page.getByText("Heavy machinery: arrival time unresolved")).toBeVisible();
  });
});
