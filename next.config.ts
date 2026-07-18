import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "crisis-damage.localhost", "*.localhost"],
  turbopack: {
    root: __dirname,
  },
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "crisis-damage-intelligence.vercel.app" }],
        destination: "https://respuestavenezuela.org/:path*",
        permanent: true,
      },
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.respuestavenezuela.org" }],
        destination: "https://respuestavenezuela.org/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
