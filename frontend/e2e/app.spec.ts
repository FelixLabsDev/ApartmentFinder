import { test, expect } from "@playwright/test";

test.describe("ApartmentFinder UI", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  // --- Layout & Structure ---

  test("renders the main layout with sidebar and content area", async ({ page }) => {
    await expect(page.locator(".sidebar")).toBeVisible();
    await expect(page.locator(".main-content")).toBeVisible();
    await expect(page.locator(".sidebar-title")).toHaveText("ApartmentFinder");
  });

  test("renders sidebar nav tabs", async ({ page }) => {
    const nav = page.locator(".sidebar-nav");
    await expect(nav).toBeVisible();
    await expect(nav.locator(".nav-tab")).toHaveCount(4);
    await expect(nav.locator(".nav-tab-scrape")).toBeVisible();
    await expect(nav.locator(".nav-tab-filters")).toBeVisible();
    await expect(nav.locator(".nav-tab-folders")).toBeVisible();
    await expect(nav.locator(".nav-tab-saved")).toBeVisible();
    // Filters tab active by default
    await expect(nav.locator(".nav-tab-filters")).toHaveClass(/active/);
  });

  test("renders the toolbar with sort dropdown and refresh button", async ({ page }) => {
    await expect(page.locator(".toolbar h1")).toHaveText("Listings");
    await expect(page.locator(".sort-select")).toBeVisible();
    await expect(page.locator(".btn-refresh")).toBeVisible();
  });

  test("renders view toggle with Grid and Map buttons", async ({ page }) => {
    const gridBtn = page.locator(".view-btn", { hasText: "Grid" });
    const mapBtn = page.locator(".view-btn", { hasText: "Map" });
    await expect(gridBtn).toBeVisible();
    await expect(mapBtn).toBeVisible();
    await expect(gridBtn).toHaveClass(/active/);
  });

  // --- Scrape Tabs ---

  test("shows scrape tab switcher with Yad2 and Facebook", async ({ page }) => {
    // Navigate to Scrape tab
    await page.locator(".nav-tab-scrape").click();
    await expect(page.locator(".scrape-tab-yad2")).toBeVisible();
    await expect(page.locator(".scrape-tab-facebook")).toBeVisible();
    // Yad2 tab active by default
    await expect(page.locator(".scrape-tab-yad2")).toHaveClass(/active/);
  });

  test("switches between Yad2 and Facebook scrape panels", async ({ page }) => {
    await page.locator(".nav-tab-scrape").click();

    // Initially Yad2 panel
    await expect(page.locator(".scrape-section-yad2")).toBeVisible();
    await expect(page.locator(".scrape-section-facebook")).not.toBeVisible();

    // Click Facebook tab
    await page.locator(".scrape-tab-facebook").click();
    await expect(page.locator(".scrape-section-facebook")).toBeVisible();
    await expect(page.locator(".scrape-section-yad2")).not.toBeVisible();
    await expect(page.locator(".scrape-tab-facebook")).toHaveClass(/active/);

    // Click back to Yad2
    await page.locator(".scrape-tab-yad2").click();
    await expect(page.locator(".scrape-section-yad2")).toBeVisible();
  });

  test("Facebook panel shows browser login toggle", async ({ page }) => {
    await page.locator(".nav-tab-scrape").click();
    await page.locator(".scrape-tab-facebook").click();
    await expect(page.locator(".browser-toggle")).toBeVisible();
    await expect(page.locator(".helper-text")).toBeVisible();
  });

  // --- Display Filters ---

  test("renders all display filter controls", async ({ page }) => {
    // Filters tab is active by default
    const section = page.locator(".display-filters-section");
    await expect(section).toBeVisible();

    // City dropdown
    await expect(section.locator("select").first()).toBeVisible();

    // Price range inputs
    const priceInputs = section.locator('input[type="number"]');
    await expect(priceInputs.first()).toBeVisible();

    // Property type dropdown
    const propertySelect = section.locator("select", { hasText: "All Types" });
    await expect(propertySelect).toBeVisible();

    // Feature checkboxes
    for (const label of ["Parking", "Elevator", "Balcony", "A/C", "Furnished", "Pet Friendly"]) {
      await expect(section.locator(".checkbox-label", { hasText: label })).toBeVisible();
    }

    // Keyword input
    await expect(section.locator(".keyword-input")).toBeVisible();

    // Liked Only toggle
    await expect(section.locator(".favorites-toggle")).toBeVisible();

    // Clear button
    await expect(section.locator(".btn-clear")).toBeVisible();
  });

  test("city filter dropdown has expected cities", async ({ page }) => {
    const citySelect = page.locator(".display-filters-section select").first();
    await expect(citySelect.locator("option")).toHaveCount(17); // "All Cities" + 16 cities
    await expect(citySelect.locator('option[value="tel-aviv"]')).toHaveText("tel-aviv");
  });

  test("property type filter has expected types", async ({ page }) => {
    const typeSelect = page.locator(".display-filters-section select", { hasText: "All Types" });
    await expect(typeSelect.locator("option")).toHaveCount(8); // "All Types" + 7 types
    await expect(typeSelect.locator('option[value="apartment"]')).toHaveText("apartment");
    await expect(typeSelect.locator('option[value="penthouse"]')).toHaveText("penthouse");
  });

  test("clear filters button resets all filters", async ({ page }) => {
    const section = page.locator(".display-filters-section");

    // Set a city filter
    const citySelect = section.locator("select").first();
    await citySelect.selectOption("tel-aviv");
    await expect(citySelect).toHaveValue("tel-aviv");

    // Clear filters
    await section.locator(".btn-clear").click();
    await expect(citySelect).toHaveValue("");
  });

  test("keyword input accepts text", async ({ page }) => {
    const input = page.locator(".keyword-input");
    await input.fill("renovated");
    await expect(input).toHaveValue("renovated");
  });

  // --- Sort Dropdown ---

  test("sort dropdown has all expected options", async ({ page }) => {
    const sortSelect = page.locator(".sort-select");
    const options = sortSelect.locator("option");
    await expect(options).toHaveCount(7);
    await expect(options.nth(0)).toHaveText("Newest First");
    await expect(options.nth(1)).toHaveText("Price: Low to High");
    await expect(options.nth(2)).toHaveText("Price: High to Low");
    await expect(options.nth(3)).toHaveText("Rooms: Fewest First");
    await expect(options.nth(4)).toHaveText("Area: Largest First");
    await expect(options.nth(5)).toHaveText("Price/m²: Low to High");
    await expect(options.nth(6)).toHaveText("Price/m²: High to Low");
  });

  test("changing sort triggers re-render", async ({ page }) => {
    const sortSelect = page.locator(".sort-select");
    await sortSelect.selectOption("price_asc");
    await expect(sortSelect).toHaveValue("price_asc");
  });

  // --- View Toggle ---

  test("clicking Map view switches to map mode", async ({ page }) => {
    const mapBtn = page.locator(".view-btn", { hasText: "Map" });
    await mapBtn.click();
    await expect(mapBtn).toHaveClass(/active/);

    // Should show map container or empty map message
    const mapContainer = page.locator(".map-container");
    const mapEmpty = page.locator(".map-empty");
    const hasMap = await mapContainer.isVisible().catch(() => false);
    const hasEmpty = await mapEmpty.isVisible().catch(() => false);
    expect(hasMap || hasEmpty).toBe(true);
  });

  test("switching back to Grid view shows listing grid", async ({ page }) => {
    // Go to map
    await page.locator(".view-btn", { hasText: "Map" }).click();
    // Go back to grid
    await page.locator(".view-btn", { hasText: "Grid" }).click();

    await expect(page.locator(".view-btn", { hasText: "Grid" })).toHaveClass(/active/);
    await expect(page.locator(".listings-grid")).toBeVisible();
  });

  // --- Stats Bar ---

  test("stats bar renders with stats", async ({ page }) => {
    // Wait for stats to load
    await expect(page.locator(".stats-bar")).toBeVisible({ timeout: 10_000 });
    const stats = page.locator(".stat");
    // Should have Total Listings, Sources, Cities
    await expect(stats).toHaveCount(3);
    await expect(page.locator(".stat-label", { hasText: "Total Listings" })).toBeVisible();
    await expect(page.locator(".stat-label", { hasText: "Sources" })).toBeVisible();
    await expect(page.locator(".stat-label", { hasText: "Cities" })).toBeVisible();
  });

  // --- Empty State ---

  test("shows empty state or listings", async ({ page }) => {
    // Wait for loading to finish
    await page.waitForTimeout(2000);

    const hasListings = await page.locator(".listing-card").first().isVisible().catch(() => false);
    const hasEmpty = await page.locator(".empty-state").isVisible().catch(() => false);
    // Should show one or the other
    expect(hasListings || hasEmpty).toBe(true);
  });

  // --- Floor Range Filter ---

  test("floor range inputs exist and accept values", async ({ page }) => {
    const section = page.locator(".display-filters-section");
    // Floor inputs are the 4th range-row (after price, rooms, area)
    const rangeRows = section.locator(".range-row");
    // Should have 5 range rows (price, rooms, area, floor, entry date)
    await expect(rangeRows).toHaveCount(5);

    const floorRow = rangeRows.nth(3);
    const minFloor = floorRow.locator('input[type="number"]').first();
    const maxFloor = floorRow.locator('input[type="number"]').last();
    await minFloor.fill("2");
    await maxFloor.fill("10");
    await expect(minFloor).toHaveValue("2");
    await expect(maxFloor).toHaveValue("10");
  });

  // --- Liked Only Toggle ---

  test("liked only toggle works", async ({ page }) => {
    const toggle = page.locator(".favorites-toggle input[type='checkbox']");
    await expect(toggle).not.toBeChecked();
    await toggle.click();
    await expect(toggle).toBeChecked();
    // Clicking again unchecks
    await toggle.click();
    await expect(toggle).not.toBeChecked();
  });

  // --- Entry Date Filter ---

  test("entry date range inputs exist and accept values", async ({ page }) => {
    const section = page.locator(".display-filters-section");
    const dateInputs = section.locator(".date-input");
    await expect(dateInputs).toHaveCount(2);
    await dateInputs.first().fill("2025-01-01");
    await expect(dateInputs.first()).toHaveValue("2025-01-01");
    await dateInputs.last().fill("2025-12-31");
    await expect(dateInputs.last()).toHaveValue("2025-12-31");
  });

  // --- Staleness / Inactive Toggle ---

  test("show taken/inactive toggle exists", async ({ page }) => {
    const toggle = page.locator(".inactive-toggle input[type='checkbox']");
    await expect(toggle).not.toBeChecked();
    await toggle.click();
    await expect(toggle).toBeChecked();
    await toggle.click();
    await expect(toggle).not.toBeChecked();
  });

  // --- Folders Panel ---

  test("folders panel renders with create form", async ({ page }) => {
    await page.locator(".nav-tab-folders").click();
    await expect(page.locator(".folders-panel")).toBeVisible();
    await expect(page.locator(".folder-create-form input")).toBeVisible();
    await expect(page.locator(".folder-create-form button")).toBeVisible();
    // "All Listings" card should be visible
    await expect(page.locator(".folder-card", { hasText: "All Listings" })).toBeVisible();
  });

  test("can create and see a folder", async ({ page }) => {
    await page.locator(".nav-tab-folders").click();
    const input = page.locator(".folder-create-form input");
    await input.fill("Test Folder");
    await page.locator(".folder-create-form button").click();
    await expect(page.locator(".folder-card", { hasText: "Test Folder" })).toBeVisible();
  });

  // --- Search Profiles ---

  test("saved searches section renders", async ({ page }) => {
    await page.locator(".nav-tab-saved").click();
    await expect(page.locator(".search-profiles h4")).toHaveText("Saved Searches");
    await expect(page.locator(".save-profile-row input")).toBeVisible();
    await expect(page.locator(".save-profile-row button")).toBeVisible();
  });

  // --- Sidebar Tab Switching ---

  test("switching between sidebar tabs shows correct panels", async ({ page }) => {
    // Default: Filters panel
    await expect(page.locator(".display-filters-section")).toBeVisible();

    // Switch to Scrape
    await page.locator(".nav-tab-scrape").click();
    await expect(page.locator(".scrape-tabs")).toBeVisible();
    await expect(page.locator(".display-filters-section")).not.toBeVisible();

    // Switch to Folders
    await page.locator(".nav-tab-folders").click();
    await expect(page.locator(".folders-panel")).toBeVisible();
    await expect(page.locator(".scrape-tabs")).not.toBeVisible();

    // Switch to Saved
    await page.locator(".nav-tab-saved").click();
    await expect(page.locator(".search-profiles")).toBeVisible();
    await expect(page.locator(".folders-panel")).not.toBeVisible();

    // Switch back to Filters
    await page.locator(".nav-tab-filters").click();
    await expect(page.locator(".display-filters-section")).toBeVisible();
  });
});

test.describe("ApartmentFinder API Integration", () => {
  test("API health endpoint responds", async ({ request }) => {
    const res = await request.get("http://localhost:8080/api/health");
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(body).toHaveProperty("sources");
  });

  test("API stats endpoint responds", async ({ request }) => {
    const res = await request.get("http://localhost:8080/api/stats");
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(body).toHaveProperty("total_listings");
    expect(body).toHaveProperty("sources");
    expect(body).toHaveProperty("cities");
  });

  test("API listings endpoint responds with filters", async ({ request }) => {
    const res = await request.get("http://localhost:8080/api/listings?limit=5&sort_by=newest");
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("API listings endpoint supports sort options", async ({ request }) => {
    for (const sort of ["newest", "price_asc", "price_desc", "rooms_asc", "area_desc"]) {
      const res = await request.get(`http://localhost:8080/api/listings?limit=1&sort_by=${sort}`);
      expect(res.ok()).toBe(true);
    }
  });

  test("API listings endpoint supports floor filter", async ({ request }) => {
    const res = await request.get("http://localhost:8080/api/listings?min_floor=1&max_floor=5&limit=5");
    expect(res.ok()).toBe(true);
  });

  test("API listings endpoint supports keyword filter", async ({ request }) => {
    const res = await request.get("http://localhost:8080/api/listings?keywords=apartment&limit=5");
    expect(res.ok()).toBe(true);
  });

  test("API neighborhoods endpoint responds for valid city", async ({ request }) => {
    const res = await request.get("http://localhost:8080/api/neighborhoods?city=tel-aviv");
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("API listings endpoint supports entry date filter", async ({ request }) => {
    const res = await request.get(
      "http://localhost:8080/api/listings?min_entry_date=2025-01-01&max_entry_date=2025-12-31&limit=5"
    );
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("API listings endpoint supports include_inactive", async ({ request }) => {
    const res = await request.get("http://localhost:8080/api/listings?include_inactive=true&limit=5");
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("API new listings endpoint responds", async ({ request }) => {
    const since = new Date(Date.now() - 86400000).toISOString();
    const res = await request.get(`http://localhost:8080/api/listings/new?since=${since}`);
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("API search profiles endpoints respond", async ({ request }) => {
    // List profiles
    const listRes = await request.get("http://localhost:8080/api/search-profiles");
    expect(listRes.ok()).toBe(true);
    const profiles = await listRes.json();
    expect(Array.isArray(profiles)).toBe(true);

    // Create a profile
    const filter = encodeURIComponent(JSON.stringify({ city: "tel-aviv" }));
    const createRes = await request.post(
      `http://localhost:8080/api/search-profiles?name=test-profile&filter_json=${filter}`
    );
    expect(createRes.ok()).toBe(true);
    const created = await createRes.json();
    expect(created).toHaveProperty("id");
    expect(created).toHaveProperty("name", "test-profile");

    // Delete the profile
    const deleteRes = await request.delete(
      `http://localhost:8080/api/search-profiles/${created.id}`
    );
    expect(deleteRes.ok()).toBe(true);
  });
});
