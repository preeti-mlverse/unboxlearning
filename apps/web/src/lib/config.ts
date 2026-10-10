// Public addresses the app links to. Set NEXT_PUBLIC_SITE_URL in each environment (e.g. https://unboxlearning.in).
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:5195").replace(/\/$/, "");
