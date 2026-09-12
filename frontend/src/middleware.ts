import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PREFIXES = ["/login", "/display"];

export function middleware(request: NextRequest) {
  if (process.env.NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED !== "true") {
    return NextResponse.next();
  }
  const { pathname } = request.nextUrl;
  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }
  if (pathname.startsWith("/_next") || pathname.startsWith("/favicon")) {
    return NextResponse.next();
  }
  const hasSession = Boolean(request.cookies.get("emic_session")?.value);
  const hasBreakGlass = Boolean(request.headers.get("authorization"));
  if (!hasSession && !hasBreakGlass) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
