/**
 * OAuth Callback Route
 * =====================
 *
 * Gère le retour des providers OAuth (Google, GitHub, Microsoft).
 * Échange le code contre une session Supabase.
 */

import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const cookieStore = await cookies();
    
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              );
            } catch {
              // Route handler context - OK
            }
          },
        },
      }
    );

    const { error } = await supabase.auth.exchangeCodeForSession(code);
    
    if (!error) {
      // Succès - rediriger vers le dashboard
      return NextResponse.redirect(`${origin}${next}`);
    }
    
    console.error("[Auth Callback] Error exchanging code:", error);
  }

  // Erreur - rediriger vers la page de login
  return NextResponse.redirect(`${origin}/login?error=auth_callback_error`);
}
