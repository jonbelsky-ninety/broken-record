// A free alternative to Vercel's paid Password Protection add-on: HTTP Basic Auth via Edge
// Middleware, included on every Vercel plan (including Hobby). Credentials come from
// environment variables set in the Vercel dashboard (Project -> Settings -> Environment
// Variables) — NEVER hardcode them here, this repo is public.
export const config = {
  matcher: "/((?!favicon.ico).*)",
};

export default function middleware(request) {
  const user = process.env.BASIC_AUTH_USER;
  const pass = process.env.BASIC_AUTH_PASS;

  // If the env vars aren't set, don't lock everyone out by accident — just pass through.
  if (!user || !pass) {
    return;
  }

  const auth = request.headers.get("authorization");
  if (auth) {
    const [scheme, encoded] = auth.split(" ");
    if (scheme === "Basic" && encoded) {
      const [suppliedUser, suppliedPass] = atob(encoded).split(":");
      if (suppliedUser === user && suppliedPass === pass) {
        return; // credentials check out — let the request through
      }
    }
  }

  return new Response("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="VoC Dashboard"' },
  });
}
