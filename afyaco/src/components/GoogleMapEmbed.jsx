// Keyless Google Maps embed — the classic "Share → Embed a map" iframe
// (https://www.google.com/maps?q=...&output=embed), not the Maps JavaScript/
// Embed API. No API key, billing or domain restrictions needed; Google
// geocodes the text query itself.
export function mapEmbedUrl(query) {
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;
}

export function mapSearchUrl(query) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

export default function GoogleMapEmbed({ query, height = 220, title = 'Map' }) {
  if (!query) return null;
  return (
    <iframe
      title={title}
      src={mapEmbedUrl(query)}
      width="100%"
      height={height}
      style={{ border: 0, borderRadius: 12, display: 'block' }}
      loading="lazy"
      referrerPolicy="no-referrer-when-downgrade"
    />
  );
}
