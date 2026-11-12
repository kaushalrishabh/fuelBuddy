import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/forgot-password", "/reset-password"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some((path) => pathname.startsWith(path));
  const hasSessionCookie = request.cookies.has("fb_token");

  if (!isPublic && !hasSessionCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isPublic && hasSessionCookie && pathname !== "/reset-password") {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|manifest.json|icons/).*)"],
};
