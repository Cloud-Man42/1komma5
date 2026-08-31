/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // The floating dev badge overlaps the kiosk layout and pollutes screenshots.
  devIndicators: false,
};

module.exports = nextConfig;
