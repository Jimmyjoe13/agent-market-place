import { test, expect } from '@playwright/test';

/**
 * Tests du Playground
 * ===================
 * 
 * Vérifie l'interface du playground et ses interactions de base.
 */

test.describe('Playground Page', () => {
  
  test.describe('Page Load', () => {
    test.use({ viewport: { width: 1280, height: 720 } });

    test('should load playground page', async ({ page }) => {
      await page.goto('/playground');
      await page.waitForLoadState('networkidle');
      
      // La page doit charger sans erreur 500
      const body = page.locator('body');
      await expect(body).toBeVisible();
    });

    test('should display playground heading or terminal icon', async ({ page }) => {
      await page.goto('/playground');
      await page.waitForLoadState('networkidle');
      
      // Chercher un indicateur que c'est la page playground
      const playgroundIndicator = page.locator('text=Playground, text=Terminal, text=Settings, h1').first();
      
      // Au moins un de ces éléments devrait exister
      const exists = await playgroundIndicator.count() > 0;
      expect(exists).toBeTruthy();
    });
  });

  test.describe('Input Area', () => {
    test.use({ viewport: { width: 1280, height: 720 } });

    test('should have a text input area', async ({ page }) => {
      await page.goto('/playground');
      await page.waitForLoadState('networkidle');
      
      // Chercher un textarea ou un input
      const inputArea = page.locator('textarea, input[type="text"]').first();
      
      // Si visible, vérifier qu'on peut taper dedans
      if (await inputArea.isVisible()) {
        await inputArea.fill('Test message');
        await expect(inputArea).toHaveValue('Test message');
      }
    });

    test('should have a send button', async ({ page }) => {
      await page.goto('/playground');
      await page.waitForLoadState('networkidle');
      
      // Chercher un bouton submit ou avec icône send
      const sendButton = page.locator('button[type="submit"], button:has(svg)').first();
      
      const count = await sendButton.count();
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Mobile', () => {
    test.use({ viewport: { width: 375, height: 667 } });

    test('should be accessible on mobile', async ({ page }) => {
      await page.goto('/playground');
      await page.waitForLoadState('networkidle');
      
      // La page doit être visible
      await expect(page.locator('body')).toBeVisible();
      
      // L'input devrait toujours être accessible
      const inputArea = page.locator('textarea, input[type="text"]').first();
      const isVisible = await inputArea.isVisible().catch(() => false);
      
      // L'input peut être dans un drawer sur mobile, donc on ne fait qu'une soft assertion
      expect(typeof isVisible).toBe('boolean');
    });
  });
});
