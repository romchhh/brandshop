/** @type {import('next').NextConfig} */
const nextConfig = {
    typescript: {
        ignoreBuildErrors: true,
    },
    /** Якщо немає файлів у public/media — проксі /media на Django (Docker: server:8000). */
    async rewrites() {
        const same = process.env.NEXT_PUBLIC_MEDIA_SAME_ORIGIN === '1' || process.env.NEXT_PUBLIC_MEDIA_SAME_ORIGIN === 'true';
        const upstream = (process.env.NEXT_PUBLIC_IMAGE_UPSTREAM || '').trim().replace(/\/$/, '');
        if (same && upstream) {
            return [{ source: '/media/:path*', destination: `${upstream}/media/:path*` }];
        }
        return [];
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
