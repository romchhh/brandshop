/** @type {import('next').NextConfig} */
const nextConfig = {
    typescript: {
        ignoreBuildErrors: true,
    },
    images: {
        loader: 'custom',
        loaderFile: './src/lib/imageLoader.ts',
        remotePatterns: [
            {
                protocol: 'https',
                hostname: '**',
            },
            {
                protocol: 'http',
                hostname: '**',
            },
        ],
        formats: ['image/avif', 'image/webp'],
        minimumCacheTTL: 86_400,
        deviceSizes: [360, 414, 640, 750, 828, 1080, 1200],
        imageSizes: [16, 32, 48, 64, 80, 96, 128, 150, 200, 256],
    },
};

export default nextConfig;
