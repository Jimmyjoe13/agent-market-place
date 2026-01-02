/**
 * Sidebar Tests
 * ===============
 *
 * Tests unitaires pour le composant Sidebar.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Sidebar } from "@/components/sidebar";

// Mock usePathname pour contrôler la route active
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/dashboard"),
}));

describe("Sidebar", () => {
  it("renders desktop sidebar with navigation icons", () => {
    render(<Sidebar />);

    // Le desktop sidebar contient des liens
    const links = screen.getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
  });

  it("renders mobile menu trigger button", () => {
    render(<Sidebar />);

    // Le bouton de menu mobile devrait être présent
    const menuButton = screen.getByRole("button", { name: /ouvrir le menu/i });
    expect(menuButton).toBeInTheDocument();
  });

  it("opens mobile menu when trigger is clicked", async () => {
    const user = userEvent.setup();
    render(<Sidebar />);

    // Cliquer sur le bouton de menu
    const menuButton = screen.getByRole("button", { name: /ouvrir le menu/i });
    await user.click(menuButton);

    // Le menu mobile devrait s'ouvrir et afficher le titre
    expect(await screen.findByText("RAG Agent")).toBeInTheDocument();
    expect(await screen.findByText("Nouvelle conversation")).toBeInTheDocument();
  });

  it("displays navigation items in mobile menu", async () => {
    const user = userEvent.setup();
    render(<Sidebar />);

    // Ouvrir le menu mobile
    const menuButton = screen.getByRole("button", { name: /ouvrir le menu/i });
    await user.click(menuButton);

    // Vérifier que les éléments de navigation sont présents
    expect(await screen.findByText("Chat")).toBeInTheDocument();
    expect(await screen.findByText("Dashboard")).toBeInTheDocument();
    expect(await screen.findByText("Clés API")).toBeInTheDocument();
    expect(await screen.findByText("Paramètres")).toBeInTheDocument();
  });

  it("has correct href for navigation links", () => {
    render(<Sidebar />);

    // Vérifier les hrefs des liens dans le desktop sidebar
    const chatLinks = screen.getAllByRole("link", { name: "" });
    const homeLink = chatLinks.find((link) => link.getAttribute("href") === "/");
    expect(homeLink).toBeDefined();
  });

  it("renders logo/branding element", () => {
    render(<Sidebar />);

    // Il devrait y avoir un lien vers la page d'accueil (le logo)
    const homeLinks = screen.getAllByRole("link").filter(
      (link) => link.getAttribute("href") === "/"
    );
    expect(homeLinks.length).toBeGreaterThan(0);
  });
});
