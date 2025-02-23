const nextConfig = {
    reactStrictMode: true,
    images: {
      domains: ['localhost'], // Allow images from localhost in development
      unoptimized: true,       // Disable Next.js image optimization (useful for diagnosing issues with `next/image`)
    },
  };
  
  module.exports = nextConfig;