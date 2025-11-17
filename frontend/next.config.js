/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_MODE: process.env.NEXT_PUBLIC_MODE || 'development',
  },
  // Remove next-intl plugin temporarily to fix __dirname issue
  // We'll handle internationalization manually in the components
};

module.exports = nextConfig;
