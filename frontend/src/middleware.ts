/**
 * NextAuth Middleware
 * ====================
 * 
 * Protège les routes console en exigeant une authentification.
 * Redirige vers /login si l'utilisateur n'est pas connecté.
 */

import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export default auth((req) => {
  const { nextUrl } = req;
  const isLoggedIn = !!req.auth;
  
  // Routes publiques (ne nécessitent pas d'auth)
  const publicRoutes = [
    "/",
    "/login",
    "/register",
    "/docs",
    "/subscription",
    "/privacy",
    "/terms",
  ];
  
  // API routes sont gérées par le backend
  const isApiRoute = nextUrl.pathname.startsWith("/api");
  
  // Static assets
  const isStaticAsset = 
    nextUrl.pathname.startsWith("/_next") ||
    nextUrl.pathname.startsWith("/static") ||
    nextUrl.pathname.includes(".");
  
  // Vérifier si route publique
  const isPublicRoute = publicRoutes.some((route) => 
    nextUrl.pathname === route || nextUrl.pathname.startsWith(`${route}/`)
  );
  
  // Laisser passer les routes publiques, API et assets
  if (isPublicRoute || isApiRoute || isStaticAsset) {
    return NextResponse.next();
  }
  
  // Rediriger vers login si non connecté
  if (!isLoggedIn) {
    const loginUrl = new URL("/login", nextUrl.origin);
    loginUrl.searchParams.set("callbackUrl", nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  
  return NextResponse.next();
});

// Matcher pour toutes les routes (sauf static files)
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|public/).*)",
  ],
};
