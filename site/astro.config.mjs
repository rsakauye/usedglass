import { defineConfig } from 'astro/config';

// SITE_URL / BASE_PATH let the same build serve Cloudflare Pages (https://usedglass.ca, base "/")
// and the GitHub Pages preview (https://rsakauye.github.io/usedglass/, base "/usedglass/").
export default defineConfig({
  site: process.env.SITE_URL || 'https://usedglass.ca',
  base: process.env.BASE_PATH || '/',
  output: 'static',
  trailingSlash: 'always',
  build: { format: 'directory' },
});
