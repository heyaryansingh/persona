const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

// S2 P0.3: allow a non-default base URL so the gate can run on a clean :8138 server
// while an idle leftover server holds :8137 (see requests/S2--to--S0--orphan-server-8137.md).
const BASE = process.env.PERSONA_SMOKE_BASE || "http://127.0.0.1:8137";

async function main() {
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
    ["C:/Program Files/Google/Chrome/Application/chrome.exe",
     "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(fs.existsSync);
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  page.on("console", msg => {
    if (msg.type() === "error" && !msg.text().includes("Failed to load resource")) consoleErrors.push(msg.text());
  });
  page.on("pageerror", err => consoleErrors.push(err.message));
  page.on("response", response => {
    if (response.status() >= 400 && !response.url().endsWith("/favicon.ico")) {
      consoleErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.evaluate(() => { openMind("curie-3c33"); setSurface("studios"); });
  await page.locator(".sessioncard").first().waitFor({ state: "visible" });

  const cards = await page.locator(".sessioncard").count();
  // Research is now the active sub-tab under the "Work" destination (Focus/Map/Work/Review).
  const researchLabel = await page.locator("#subbar button.on").innerText();
  if (cards < 3) throw new Error(`expected at least three research sessions, got ${cards}`);
  if (!researchLabel.includes("Research")) throw new Error(`unexpected navigation label: ${researchLabel}`);
  await page.screenshot({ path: path.resolve("results/ui_research_sessions.png"), fullPage: true });

  const geoSession = page.locator(".sessioncard.contested").filter({ hasText: "Matched-donor GEO self-test" }).first();
  await geoSession.waitFor({ state: "visible" });
  await geoSession.click();
  await page.locator(".auditbox").waitFor({ state: "visible" });
  const modalText = await page.locator("#modalbox").innerText();
  const modalTextLower = modalText.toLowerCase();
  for (const expected of ["trace integrity · passes", "2/2 required claims cited",
                           "evidence-linked conclusions", "latest review-adjusted figure",
                           "public execution trace", "expression proxy, not causality",
                           "scientific review · contested"]) {
    if (!modalTextLower.includes(expected)) throw new Error(`missing session detail: ${expected}\n${modalText.slice(0, 1600)}`);
  }
  const figure = page.locator("#modalbox .sessionfigure").first();
  await figure.waitFor({ state: "visible" });
  if ((await figure.getAttribute("src") || "").includes("undefined")) throw new Error("bad figure URL");
  await page.screenshot({ path: path.resolve("results/ui_research_session_detail.png"), fullPage: true });
  await page.screenshot({ path: path.resolve("results/ui_research_geo_session.png"), fullPage: true });

  await page.evaluate(() => { closeModal(); setSurface("instruments"); });
  const dossierButton = page.getByRole("button", { name: "open evidence dossier" }).first();
  await dossierButton.waitFor({ state: "visible" });
  await dossierButton.click();
  await page.locator(".dossiergrid").waitFor({ state: "visible" });
  await page.waitForTimeout(350);
  const dossierText = (await page.locator("#modalbox").innerText()).toLowerCase();
  for (const expected of ["why persona is asking", "context not yet structured",
                           "discriminating checks", "record a scoped human review",
                           "belief unchanged", "extraction error", "insufficient evidence"]) {
    if (!dossierText.includes(expected)) throw new Error(`missing conflict dossier detail: ${expected}`);
  }
  await page.screenshot({ path: path.resolve("results/ui_conflict_dossier.png"), fullPage: true });

  if (consoleErrors.length) throw new Error(`browser console errors: ${consoleErrors.join(" | ")}`);
  console.log(JSON.stringify({ cards, researchLabel: researchLabel.trim(), geoSession: "passed", conflictDossier: "passed" }));
  await browser.close();
}

main().catch(error => { console.error(error); process.exit(1); });
