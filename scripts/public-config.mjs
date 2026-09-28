// Only values intended for every browser visitor may be emitted here.
export const publicNames = [
  'SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'MUUMEI_APP_URL',
  'VAPID_PUBLIC_KEY', 'MUUMEI_PRODUCTION_READY', 'MUUMEI_OPERATOR_NAME',
  'MUUMEI_OPERATOR_ADDRESS', 'MUUMEI_OPERATOR_CONTACT',
];

export function createPublicConfig(values) {
  const get = name => typeof values[name] === 'string' ? values[name].trim() : '';
  const key = get('SUPABASE_PUBLISHABLE_KEY');
  if (key && !/^sb_publishable_[A-Za-z0-9_-]+$/.test(key)) {
    throw new Error('SUPABASE_PUBLISHABLE_KEY must be a publishable key. Secret and legacy keys cannot be exported.');
  }
  const origin = name => {
    const value = get(name);
    if (!value) return '';
    let url;
    try { url = new URL(value); } catch { throw new Error(`${name} must be an HTTPS origin.`); }
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
      throw new Error(`${name} must be an HTTPS origin without credentials, query, fragment or subpath.`);
    }
    return url.origin;
  };
  const config = {
    url: origin('SUPABASE_URL'), key, appUrl: origin('MUUMEI_APP_URL'),
    vapid: get('VAPID_PUBLIC_KEY'), ready: get('MUUMEI_PRODUCTION_READY') === 'true',
    operator: {name: get('MUUMEI_OPERATOR_NAME'), address: get('MUUMEI_OPERATOR_ADDRESS'), contact: get('MUUMEI_OPERATOR_CONTACT')},
  };
  if (Boolean(config.url) !== Boolean(config.key)) throw new Error('SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be set together.');
  if (config.ready && (!config.url || !config.key || !config.appUrl || Object.values(config.operator).some(v => !v))) {
    throw new Error('Production readiness requires the app origin, backend and operator information.');
  }
  return config;
}

export const staticHeaders = `/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  X-Frame-Options: DENY
  Cache-Control: no-cache
/muumei-config.json
  Cache-Control: no-store
`;

export const staticRedirects = '/* /index.html 200\n';
