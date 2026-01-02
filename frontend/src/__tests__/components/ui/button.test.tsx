/**
 * Button Component Tests
 * =========================
 *
 * Tests unitaires pour le composant Button UI.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders with default variant", () => {
    render(<Button>Click me</Button>);

    const button = screen.getByRole("button", { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute("data-variant", "default");
  });

  it("renders with destructive variant", () => {
    render(<Button variant="destructive">Delete</Button>);

    const button = screen.getByRole("button", { name: /delete/i });
    expect(button).toHaveAttribute("data-variant", "destructive");
  });

  it("renders with outline variant", () => {
    render(<Button variant="outline">Outline</Button>);

    const button = screen.getByRole("button", { name: /outline/i });
    expect(button).toHaveAttribute("data-variant", "outline");
  });

  it("renders with ghost variant", () => {
    render(<Button variant="ghost">Ghost</Button>);

    const button = screen.getByRole("button", { name: /ghost/i });
    expect(button).toHaveAttribute("data-variant", "ghost");
  });

  it("handles click events", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(<Button onClick={handleClick}>Click me</Button>);

    await user.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("can be disabled", () => {
    render(<Button disabled>Disabled</Button>);

    const button = screen.getByRole("button", { name: /disabled/i });
    expect(button).toBeDisabled();
  });

  it("renders different sizes", () => {
    const { rerender } = render(<Button size="sm">Small</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("data-size", "sm");

    rerender(<Button size="lg">Large</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("data-size", "lg");

    rerender(<Button size="icon">Icon</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("data-size", "icon");
  });

  it("renders as child when asChild is true", () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    );

    const link = screen.getByRole("link", { name: /link button/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/test");
  });
});
