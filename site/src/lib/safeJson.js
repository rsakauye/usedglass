// JSON text that is safe to put inside an inline <script> element.
// `<` `>` `&` and the two line-separator characters can end or confuse a script element,
// so they become unicode escapes. JSON.parse turns them back into the same characters.
const LS = String.fromCharCode(0x2028);
const PS = String.fromCharCode(0x2029);
const esc = (code) => '\\u' + code.toString(16).padStart(4, '0');

export function safeJson(value) {
  return JSON.stringify(value)
    .replace(/</g, esc(0x3c))
    .replace(/>/g, esc(0x3e))
    .replace(/&/g, esc(0x26))
    .split(LS).join(esc(0x2028))
    .split(PS).join(esc(0x2029));
}
