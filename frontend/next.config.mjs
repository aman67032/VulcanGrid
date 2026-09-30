/** @type {import('next').NextConfig} */
const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === 'production' || process.env.VERCEL
    ? 'https://backend-eta-steel-90.vercel.app'
    : 'http://localhost:8000');

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl.replace(/\/$/, '')}/:path*`,
      },
    ];
  },
};

export default nextConfig;
