import QRCode from 'qrcode';

export function authenticatorIssuer(website?: string): string {
  if (website === undefined) return 'MH'; // Previously issued setup responses.
  const site = new URL(website);
  if (!['http:', 'https:'].includes(site.protocol) || !site.hostname || site.username || site.password || site.search || site.hash || site.pathname !== '/') {
    throw new Error('Invalid authenticator website');
  }
  const host = site.hostname.replace(/^\[|\]$/g, '').replace(/:/g, '·');
  return `MH · ${host}${site.port ? ` (${site.port})` : ''}`;
}

// Encode only this account's TOTP setup URI, entirely inside the browser.
// Never send the URI/secret to an image host or a QR-code service.
export async function authenticatorQr(uri: string, secret: string, email: string, website?: string): Promise<string> {
  const value = new URL(uri);
  const issuer = authenticatorIssuer(website);
  if (value.protocol !== 'otpauth:' || value.hostname !== 'totp' || value.username || value.password || value.hash ||
      decodeURIComponent(value.pathname.slice(1)) !== `${issuer}:${email}` ||
      !/^[A-Z2-7]{32}$/.test(secret) || value.searchParams.get('secret') !== secret || value.searchParams.get('issuer') !== issuer ||
      (value.searchParams.get('algorithm') || 'SHA1') !== 'SHA1' ||
      (value.searchParams.get('digits') || '6') !== '6' || (value.searchParams.get('period') || '30') !== '30') {
    throw new Error('Invalid authenticator setup');
  }
  return QRCode.toDataURL(uri, { type: 'image/png', errorCorrectionLevel: 'M', margin: 4, scale: 6, color: { dark: '#000000', light: '#ffffff' } });
}
