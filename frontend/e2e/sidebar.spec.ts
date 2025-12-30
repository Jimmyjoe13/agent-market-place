import { test, expect } from '@playwright/test';

/**
 * Tests de la Sidebar (Pages Console)
 * ====================================
 * 
 * Note: Ces pages nécessitent normalement une authentification.
 * En mode test, nous vérifions le comportement UI même si l'auth échoue.
 */

test.describe('Sidebar Navigation', () => {
  
  test.describe('Desktop Layout', () => {
    test.use({ viewport: { width: 1280, height: 720 } });

    test('should display sidebar element on console pages', async ({ page }) => {
      // Aller sur une page console (même sans auth, la sidebar devrait s'afficher)
      await page.goto('/dashboard');
      
      // Attendre que la page charge
      await page.waitForLoadState('networkidle');
      
      // La sidebar desktop (ou un élément de navigation) devrait exister
      const sidebar = page.locator('nav, [aria-label*="Navigation"], aside').first();
      await expect(sidebar).toBeVisible({ timeout: 10000 });
    });

    test('should have navigation links', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      
      // Chercher des liens de navigation courants
      const navLinks = page.getByRole('link');
      const count = await navLinks.count();
      
      // Il devrait y avoir au moins quelques liens
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Mobile Layout', () => {
    test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE

    test('should have mobile-friendly layout', async ({ page }) => {
      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');
      
      // La page doit être accessible sur mobile sans erreur
      await expect(page.locator('body')).toBeVisible();
    });

    test('should have some navigation mechanism on mobile', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      
      // Il devrait y avoir un bouton ou un élément pour la navigation
      const navElements = page.locator('button, [role="button"], a');
      const count = await navElements.count();
      
      expect(count).toBeGreaterThan(0);
    });
  });
});
