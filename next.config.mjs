/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
};

export default nextConfig;
