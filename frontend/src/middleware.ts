/**
 * NextAuth Middleware
 * ====================
 * 
 * Protège les routes console en exigeant une authentification.
 * Le callback 'authorized' dans auth.ts gère la logique de protection.
 */

export { auth as middleware } from "@/lib/auth";

// Configuration du matcher pour les routes à protéger
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
