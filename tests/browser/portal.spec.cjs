const { test, expect } = require("playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

async function openPortal(page, hash = "#home") {
  await page.goto(`/${hash}`);
  await expect(page.locator("#boot-screen")).toHaveClass(/done/, { timeout: 30000 });
  await expect(page.locator("#main")).not.toBeEmpty();
}

test.beforeEach(async ({ page }) => {
  // Keep these tests deterministic and isolated from live user/application data.
  await page.route("https://yipzokjzqltxcufixrsv.supabase.co/**", route =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "content-range": "0-0/0" },
      body: "[]"
    })
  );
});

test("primary navigation renders each public section without runtime errors", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await openPortal(page);

  for (const key of ["home", "standings", "results", "calendar", "entries", "rules", "apply", "status"]) {
    const link = page.locator(`#nav a[data-nav="${key}"]`);
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(new RegExp(`#${key}$`));
    await expect(page.locator("#main")).not.toBeEmpty();
  }
  expect(pageErrors).toEqual([]);
});

test("championship statistics dropdown opens, closes, and opens repeatedly", async ({ page }) => {
  await openPortal(page);
  const details = page.locator(".champion-more").first();
  await expect(details).toBeVisible();
  const summary = details.locator("summary");

  await summary.click();
  await expect(details).toHaveAttribute("open", "");
  await expect.poll(() => details.locator(".champion-stats-clip").evaluate(el =>
    el.getBoundingClientRect().height
  )).toBeGreaterThan(0);

  await summary.click();
  await expect(details).not.toHaveAttribute("open", "");
  await summary.click();
  await expect(details).toHaveAttribute("open", "");
  await expect.poll(() => details.locator(".champion-stats-clip").evaluate(el =>
    el.getBoundingClientRect().height
  )).toBeGreaterThan(0);
});

test("driver season picker can be opened, selected, and reopened", async ({ page }) => {
  await openPortal(page, "#standings");
  const driverLink = page.locator('a[href^="#driver/"]').first();
  if (!(await driverLink.count())) test.skip(true, "No driver profile link is present in the current workbook.");
  await driverLink.click();
  const trigger = page.locator("#driver-season-trigger");
  await expect(trigger).toBeVisible();
  await trigger.click();
  await expect(trigger).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("#driver-season-menu")).toBeVisible();

  const option = page.locator("#driver-season-menu [data-driver-season]").first();
  if (await option.count()) await option.click();
  await trigger.click();
  await expect(trigger).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("#driver-season-menu")).toBeVisible();
});

test("home page has no critical axe accessibility violations", async ({ page }) => {
  await openPortal(page);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const critical = results.violations.filter(item => item.impact === "critical");
  expect(critical.map(item => ({ id: item.id, description: item.description }))).toEqual([]);
});

test("home page does not introduce horizontal overflow at common viewport widths", async ({ page }) => {
  await openPortal(page);
  for (const width of [390, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    const overflow = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth
    }));
    expect(overflow.document, `document overflow at ${width}px: ${JSON.stringify(overflow)}`).toBeLessThanOrEqual(width + 1);
    expect(overflow.body, `body overflow at ${width}px: ${JSON.stringify(overflow)}`).toBeLessThanOrEqual(width + 1);
  }
});
