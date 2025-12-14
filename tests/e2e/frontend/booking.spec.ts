import { test, expect } from '@playwright/test';

test.describe('EduSched Frontend E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');

    // Wait for the app to load
    await page.waitForSelector('[data-testid="app-loaded"]', { timeout: 10000 });
  });

  test.describe('Navigation', () => {
    test('TC-FE-NAV-001: Application initializes correctly', async ({ page }) => {
      // Verify the main app container exists
      await expect(page.locator('[data-testid="app-container"]')).toBeVisible();

      // Verify no JavaScript errors
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.waitForLoadState('networkidle');
      expect(errors).toHaveLength(0);
    });

    test('TC-FE-NAV-002: Navigate to all main routes', async ({ page }) => {
      const routes = [
        { path: '/dashboard', name: 'Dashboard' },
        { path: '/schedules', name: 'Schedules' },
        { path: '/resources', name: 'Resources' },
        { path: '/constraints', name: 'Constraints' },
        { path: '/optimization', name: 'Optimization' },
        { path: '/analytics', name: 'Analytics' },
      ];

      for (const route of routes) {
        // Click on navigation link
        await page.click(`[data-testid="nav-${route.name.toLowerCase()}"]`);

        // Verify URL changed
        expect(page.url()).toContain(route.path);

        // Verify page title
        await expect(page.locator('h1')).toContainText(route.name);

        // Verify page content loaded
        await expect(page.locator(`[data-testid="${route.name.toLowerCase()}-page"]`)).toBeVisible();
      }
    });

    test('TC-FE-NAV-003: 404 page for invalid routes', async ({ page }) => {
      // Navigate to invalid route
      await page.goto('/invalid-route');

      // Verify 404 page
      await expect(page.locator('[data-testid="not-found-page"]')).toBeVisible();
      await expect(page.locator('h1')).toContainText('Page Not Found');
    });
  });

  test.describe('Dashboard', () => {
    test('TC-FE-DATA-001: Dashboard loads and displays data', async ({ page }) => {
      // Navigate to dashboard
      await page.click('[data-testid="nav-dashboard"]');

      // Verify loading state
      await expect(page.locator('[data-testid="dashboard-loading"]')).toBeVisible();

      // Wait for data to load
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();

      // Verify metrics are displayed
      await expect(page.locator('[data-testid="total-schedules"]')).toBeVisible();
      await expect(page.locator('[data-testid="active-schedules"]')).toBeVisible();
      await expect(page.locator('[data-testid="resource-utilization"]')).toBeVisible();
      await expect(page.locator('[data-testid="recent-activities"]')).toBeVisible();
    });

    test('Dashboard handles API errors gracefully', async ({ page }) => {
      // Mock API failure
      await page.route('**/api/dashboard/stats', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal server error' })
        });
      });

      await page.click('[data-testid="nav-dashboard"]');

      // Verify error message displays
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    });
  });

  test.describe('Schedules', () => {
    test('TC-FE-DATA-002: Schedule list with pagination and filters', async ({ page }) => {
      await page.click('[data-testid="nav-schedules"]');

      // Verify list loads
      await expect(page.locator('[data-testid="schedule-list"]')).toBeVisible();

      // Test search
      await page.fill('[data-testid="schedule-search"]', 'Test Schedule');
      await page.press('[data-testid="schedule-search"]', 'Enter');

      // Verify filtered results
      const scheduleItems = page.locator('[data-testid="schedule-item"]');
      const count = await scheduleItems.count();

      for (let i = 0; i < count; i++) {
        await expect(scheduleItems.nth(i)).toContainText('Test Schedule');
      }

      // Test pagination
      if (count > 0) {
        await page.click('[data-testid="next-page"]');
        await page.waitForLoadState('networkidle');
      }
    });

    test('TC-FE-INT-001: Create new schedule workflow', async ({ page }) => {
      await page.click('[data-testid="nav-schedules"]');
      await page.click('[data-testid="new-schedule-btn"]');

      // Verify form appears
      await expect(page.locator('[data-testid="schedule-form"]')).toBeVisible();

      // Fill form
      await page.fill('[data-testid="schedule-name"]', 'E2E Test Schedule');
      await page.selectOption('[data-testid="solver-select"]', 'heuristic');
      await page.check('[data-testid="optimize-checkbox"]');

      // Add constraints
      await page.click('[data-testid="add-constraint-btn"]');
      await page.selectOption('[data-testid="constraint-type"]', 'time_window');
      await page.fill('[data-testid="constraint-start"]', '09:00');
      await page.fill('[data-testid="constraint-end"]', '17:00');

      // Submit form
      await page.click('[data-testid="submit-schedule"]');

      // Verify success notification
      await expect(page.locator('[data-testid="success-notification"]')).toBeVisible();

      // Verify redirect to schedule details
      await expect(page.url()).toMatch(/\/schedules\/[a-zA-Z0-9-]+/);
    });

    test('TC-FE-DATA-003: Schedule details view', async ({ page }) => {
      // First navigate to schedules list
      await page.click('[data-testid="nav-schedules"]');

      // Wait for list to load
      await page.waitForSelector('[data-testid="schedule-item"]');

      // Click on first schedule
      await page.click('[data-testid="schedule-item"]:first-child');

      // Verify schedule details
      await expect(page.locator('[data-testid="schedule-details"]')).toBeVisible();
      await expect(page.locator('[data-testid="schedule-info"]')).toBeVisible();
      await expect(page.locator('[data-testid="assignments-calendar"]')).toBeVisible();
      await expect(page.locator('[data-testid="schedule-stats"]')).toBeVisible();

      // Verify export options
      await expect(page.locator('[data-testid="export-menu"]')).toBeVisible();
    });

    test('TC-FE-INT-002: Edit schedule', async ({ page }) => {
      // Navigate to a schedule
      await page.goto('/schedules');
      await page.click('[data-testid="schedule-item"]:first-child');

      // Click edit button
      await page.click('[data-testid="edit-schedule-btn"]');

      // Verify edit form
      await expect(page.locator('[data-testid="schedule-form"]')).toBeVisible();

      // Modify schedule name
      await page.fill('[data-testid="schedule-name"]', 'Updated Schedule Name');

      // Save changes
      await page.click('[data-testid="save-changes"]');

      // Verify update notification
      await expect(page.locator('[data-testid="update-notification"]')).toBeVisible();

      // Verify name updated
      await expect(page.locator('[data-testid="schedule-name-display"]')).toHaveText('Updated Schedule Name');
    });

    test('TC-FE-INT-003: Drag and drop assignments', async ({ page }) => {
      // Navigate to schedule with calendar view
      await page.goto('/schedules');
      await page.click('[data-testid="schedule-item"]:first-child');
      await page.click('[data-testid="calendar-view"]');

      // Wait for assignments to load
      await page.waitForSelector('[data-testid="assignment"]');

      // Get first assignment
      const assignment = page.locator('[data-testid="assignment"]:first-child');

      // Get target time slot
      const targetSlot = page.locator('[data-testid="time-slot"]:nth-child(3)');

      // Drag assignment to new slot
      await assignment.dragTo(targetSlot);

      // Verify move dialog appears
      await expect(page.locator('[data-testid="move-confirmation"]')).toBeVisible();

      // Confirm move
      await page.click('[data-testid="confirm-move"]');

      // Verify success notification
      await expect(page.locator('[data-testid="move-success"]')).toBeVisible();
    });

    test('TC-FE-DATA-004: Real-time updates via WebSocket', async ({ page }) => {
      // Navigate to schedule details
      await page.goto('/schedules');
      await page.click('[data-testid="schedule-item"]:first-child');

      // Listen for WebSocket messages
      const wsMessages: any[] = [];
      page.on('websocket', ws => {
        ws.on('framesent', event => console.log('Sent:', event.payload));
        ws.on('framereceived', event => {
          wsMessages.push(JSON.parse(event.payload as string));
        });
      });

      // Make changes via API (simulated)
      await page.evaluate(() => {
        // Simulate an external update
        const event = new CustomEvent('scheduleUpdate', {
          detail: {
            scheduleId: 'test-id',
            changes: { status: 'published' }
          }
        });
        window.dispatchEvent(event);
      });

      // Verify update notification appears
      await expect(page.locator('[data-testid="realtime-update"]')).toBeVisible();
    });
  });

  test.describe('Forms and Validation', () => {
    test('TC-FE-VAL-001: Form validation for required fields', async ({ page }) => {
      await page.click('[data-testid="nav-schedules"]');
      await page.click('[data-testid="new-schedule-btn"]');

      // Try to submit without filling required fields
      await page.click('[data-testid="submit-schedule"]');

      // Verify validation errors
      await expect(page.locator('[data-testid="error-name-required"]')).toBeVisible();

      // Fill name and try again
      await page.fill('[data-testid="schedule-name"]', 'Valid Name');
      await page.click('[data-testid="submit-schedule"]');

      // Verify name error is gone
      await expect(page.locator('[data-testid="error-name-required"]')).not.toBeVisible();
    });

    test('TC-FE-VAL-002: Invalid data handling', async ({ page }) => {
      await page.goto('/schedules/new');

      // Try invalid time values
      await page.fill('[data-testid="constraint-start"]', '25:00'); // Invalid time
      await page.fill('[data-testid="constraint-end"]', '08:00'); // End before start

      // Verify validation errors
      await expect(page.locator('[data-testid="error-invalid-time"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-time-range"]')).toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {
    test('TC-FE-RES-001: Desktop layout', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('/');

      // Verify desktop navigation
      await expect(page.locator('[data-testid="desktop-sidebar"]')).toBeVisible();
      await expect(page.locator('[data-testid="main-content"]')).toBeVisible();
    });

    test('TC-FE-RES-002: Tablet layout', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/');

      // Verify tablet navigation adapts
      await expect(page.locator('[data-testid="mobile-menu-btn"]')).toBeVisible();
      await page.click('[data-testid="mobile-menu-btn"]');
      await expect(page.locator('[data-testid="mobile-nav"]')).toBeVisible();
    });

    test('TC-FE-RES-003: Mobile layout', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/');

      // Verify mobile layout
      await expect(page.locator('[data-testid="mobile-header"]')).toBeVisible();

      // Test mobile navigation
      await page.click('[data-testid="mobile-menu-btn"]');
      await expect(page.locator('[data-testid="mobile-nav-drawer"]')).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('TC-FE-VAL-003: Network error handling', async ({ page }) => {
      // Simulate network offline
      await page.context().setOffline(true);

      await page.click('[data-testid="nav-schedules"]');

      // Verify offline message
      await expect(page.locator('[data-testid="offline-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();

      // Restore network
      await page.context().setOffline(false);

      // Click retry
      await page.click('[data-testid="retry-button"]');

      // Verify content loads
      await expect(page.locator('[data-testid="schedule-list"]')).toBeVisible();
    });

    test('Server error handling', async ({ page }) => {
      // Mock server error
      await page.route('**/api/schedules', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Database connection failed' })
        });
      });

      await page.click('[data-testid="nav-schedules"]');

      // Verify error page
      await expect(page.locator('[data-testid="server-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-details"]')).toContainText('Database connection failed');
    });
  });

  test.describe('Performance', () => {
    test('Page load performance', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const loadTime = Date.now() - startTime;

      // Verify load time is acceptable (< 3 seconds)
      expect(loadTime).toBeLessThan(3000);
    });

    test('Large dataset handling', async ({ page }) => {
      // Mock large dataset
      await page.route('**/api/schedules', route => {
        const schedules = Array.from({ length: 1000 }, (_, i) => ({
          id: `schedule-${i}`,
          name: `Schedule ${i}`,
          status: 'active'
        }));

        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ schedules, total: 1000 })
        });
      });

      await page.click('[data-testid="nav-schedules"]');

      // Verify pagination or virtualization is used
      await expect(page.locator('[data-testid="pagination"]')).toBeVisible();

      // Verify smooth scrolling
      const items = await page.locator('[data-testid="schedule-item"]').count();
      expect(items).toBeLessThan(100); // Should not render all at once
    });
  });
});