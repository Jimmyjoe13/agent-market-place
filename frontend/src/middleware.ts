/**
 * Supabase Auth Middleware
 * =========================
 *
 * Protège les routes console en vérifiant la session Supabase.
 * Rafraîchit automatiquement les tokens expirés.
 */

import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Routes publiques (pas d'auth requise)
const publicRoutes = [
  "/",
  "/login",
  "/register",
  "/docs",
  "/subscription",
  "/privacy",
  "/terms",
  "/auth/callback",
];

// Routes protégées (auth requise)
const protectedPrefixes = ["/dashboard", "/keys", "/playground", "/settings", "/billing"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip pour les assets statiques
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Vérifier si route publique
  const isPublicRoute = publicRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );

  // Créer la réponse
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  // Créer le client Supabase
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          );
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // Rafraîchir la session (important pour le SSR)
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Vérifier si la route est protégée
  const isProtectedRoute = protectedPrefixes.some((prefix) =>
    pathname.startsWith(prefix)
  );

  // Rediriger vers login si pas connecté sur route protégée
  if (isProtectedRoute && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(url);
  }

  // Rediriger vers dashboard si connecté et sur login/register
  if (user && (pathname === "/login" || pathname === "/register")) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  return response;
}

// Configuration du matcher
export const config = {
  matcher: [
    /*
     * Match toutes les routes sauf :
     * - _next/static (fichiers statiques)
     * - _next/image (optimisation d'images)
     * - favicon.ico
     * - Fichiers publics (images, etc.)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
