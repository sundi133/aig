/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    AIG_BACKEND_URL: process.env.AIG_BACKEND_URL || "http://localhost:8080",
    AIG_ADMIN_TOKEN: process.env.AIG_ADMIN_TOKEN || "admin-dev-token",
  },
};

module.exports = nextConfig;
