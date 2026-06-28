import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
