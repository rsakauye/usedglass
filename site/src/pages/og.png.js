// Social share image (1200x630), rendered at build time from the site's own logo with sharp (bundled with Astro).
// If sharp is unavailable the build still succeeds and falls back to apple-touch-icon.png.
import fs from 'node:fs';
import path from 'node:path';
const SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#111"/><g transform="translate(90,175) scale(4.4)"><rect x="35" y="12" width="9" height="5" rx="2" fill="#f4a261"/><rect x="6" y="16" width="44" height="32" rx="6" fill="#fff"/><path d="M11 17 L14 10.5 H23 L26 17 Z" fill="#fff" stroke="#fff" stroke-width="2" stroke-linejoin="round"/><rect x="38" y="21" width="7" height="4" rx="1.5" fill="#2a9df4"/><path d="M39.5 40.5 L56 57" stroke="#fff" stroke-width="7.5" stroke-linecap="round"/><path d="M41 42 L55.5 56.5" stroke="#f4a261" stroke-width="3" stroke-linecap="round"/><circle cx="28" cy="32" r="13" fill="#14213d"/><circle cx="28" cy="32" r="11" fill="#fff"/><circle cx="28" cy="32" r="9.2" fill="#14213d"/><circle cx="28" cy="32" r="7.2" fill="#2a9df4"/><path d="M23.5 29a5.5 5.5 0 0 1 4.5-3" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round"/></g><text x="420" y="300" font-family="DejaVu Sans, sans-serif" font-weight="bold" font-size="92" fill="#fff">Used<tspan fill="#7cc4ff">Glass</tspan>.ca</text><text x="424" y="380" font-family="DejaVu Sans, sans-serif" font-size="40" fill="#d0d4dc">Used camera &amp; lens prices in Canada</text><text x="424" y="440" font-family="DejaVu Sans, sans-serif" font-size="30" fill="#f4a261">Canadian dealers, updated daily</text></svg>`;
export async function GET() {
  try {
    const { default: sharp } = await import('sharp');
    const png = await sharp(Buffer.from(SVG)).png().toBuffer();
    return new Response(png, { headers: { 'Content-Type': 'image/png' } });
  } catch (e) {
    console.warn('[og.png] sharp unavailable, using fallback:', e.message);
    return new Response(fs.readFileSync(path.resolve(process.cwd(), 'public', 'apple-touch-icon.png')), { headers: { 'Content-Type': 'image/png' } });
  }
}
