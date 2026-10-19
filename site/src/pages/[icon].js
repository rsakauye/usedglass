import { ICONS } from '../lib/icons.js';

// Emits /favicon.ico, /favicon-16.png, /favicon-32.png and /apple-touch-icon.png as static files.
export function getStaticPaths() {
  return Object.keys(ICONS).map((icon) => ({ params: { icon } }));
}

const TYPES = { ico: 'image/x-icon', png: 'image/png' };

export function GET({ params }) {
  const ext = params.icon.split('.').pop();
  return new Response(Buffer.from(ICONS[params.icon], 'base64'), {
    headers: { 'Content-Type': TYPES[ext] || 'application/octet-stream' },
  });
}
