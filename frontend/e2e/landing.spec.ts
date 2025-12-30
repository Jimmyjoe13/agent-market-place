import { test, expect } from '@playwright/test';

/**
 * Tests de la Landing Page (Publique)
 * ===================================
 * 
 * Ces tests ne nécessitent pas d'authentification.
 */

test.describe('Landing Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display hero section', async ({ page }) => {
    // Vérifier que la page charge
    await expect(page).toHaveTitle(/RAG Agent/i);
    
    // Vérifier le titre principal (h1)
    const heading = page.locator('h1');
    await expect(heading).toBeVisible();
  });

  test('should display CTA buttons', async ({ page }) => {
    // Bouton "Démarrer gratuitement" ou équivalent
    const ctaButton = page.getByRole('link', { name: /commencer|démarrer/i });
    await expect(ctaButton.first()).toBeVisible();
  });

  test('should navigate to register page when clicking CTA', async ({ page }) => {
    const ctaButton = page.getByRole('link', { name: /commencer gratuitement/i }).first();
    await ctaButton.click();
    
    await expect(page).toHaveURL(/register/);
  });

  test('should have working navigation links', async ({ page }) => {
    // Vérifier le lien Documentation
    const docsLink = page.getByRole('link', { name: /documentation/i }).first();
    await expect(docsLink).toBeVisible();
  });

  test('should display pricing section', async ({ page }) => {
    // Scroller vers pricing
    await page.evaluate(() => {
      const pricing = document.querySelector('#pricing');
      pricing?.scrollIntoView();
    });
    
    // Vérifier que "Tarifs" ou "Free" est visible
    await expect(page.getByText(/Free|Gratuit/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('should be responsive on mobile', async ({ page, isMobile }) => {
    // La page doit charger sans erreur sur mobile
    await expect(page.locator('body')).toBeVisible();
    
    if (isMobile) {
      // Sur mobile, les boutons CTA doivent être accessibles
      const ctaButton = page.getByRole('link', { name: /commencer/i }).first();
      await expect(ctaButton).toBeVisible();
    }
  });
});
