const nextConfig = {
  reactStrictMode: true,

  experimental: {
    runtime: "edge",
  },
  images: {
    domains: ['localhost', 'backend-production-9811.up.railway.app'], 
    unoptimized: process.env.NODE_ENV === 'development',
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === "production", // Remove console logs in production
  },
  swcMinify: true,
};

module.exports = nextConfig;
