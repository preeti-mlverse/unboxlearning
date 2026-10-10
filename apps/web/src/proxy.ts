// Send people who aren't signed in to the log-in page before rendering anything private.
// This is only a convenience: every API call is still authorised by the API itself.
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC = ["/login", "/signup", "/forgot-password", "/reset-password", "/verify-email", "/session-expired", "/unauthorized"];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (PUBLIC.some((p) => pathname === p || pathname.startsWith(p + "/"))) return NextResponse.next();
  const signedIn = request.cookies.has("ub_refresh") || request.cookies.has("ub_access");
  if (!signedIn) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = pathname === "/" ? "" : `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api/|_next/|favicon|icon|apple-touch|brand/|.*\\.(?:png|svg|ico|webp|jpg)$).*)"],
};
