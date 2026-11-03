import { locale } from "./i18n";
import catalogJson from '../../pricing_catalog.json';

export type Product = { name: string; cents: number; tokens: number; seats?: number; kind: 'subscription' | 'payment'; interval?: 'month' | 'year' };
export const catalog = catalogJson as Record<string, Product>;
export const planKeys = ['starter', 'team', 'scale'] as const;
export const topupKeys = ['tokens_250', 'tokens_1000', 'tokens_2500'] as const;
export type BillingCycle = 'month' | 'year';
export const price = (cents: number) => new Intl.NumberFormat(locale, { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(cents / 100);

export function cheapestTopup(requiredTokens: number) {
  if (requiredTokens <= 0) return { cents: 0, tokens: 0, packs: [] as { sku: string; quantity: number }[] };
  const items = topupKeys.map(sku => ({ sku, ...catalog[sku] }));
  const unit = 250;
  const target = Math.ceil(requiredTokens / unit);
  let best: { cents: number; tokens: number; packs: { sku: string; quantity: number }[] } | null = null;
  // Search covers the calculator's 0-100 campaign packages and permits slight overbuying when cheaper.
  for (let large = 0; large <= Math.ceil(target / 10) + 1; large++) {
    for (let medium = 0; medium <= Math.ceil(target / 4) + 1; medium++) {
      const remaining = Math.max(0, target - large * 10 - medium * 4);
      for (const small of [remaining, remaining + 1]) {
        const quantities = [small, medium, large];
        const tokens = quantities.reduce((sum, count, i) => sum + count * items[i].tokens, 0);
        const cents = quantities.reduce((sum, count, i) => sum + count * items[i].cents, 0);
        if (tokens < requiredTokens) continue;
        if (!best || cents < best.cents || (cents === best.cents && tokens < best.tokens)) {
          best = { cents, tokens, packs: quantities.flatMap((quantity, i) => quantity ? [{ sku: items[i].sku, quantity }] : []) };
        }
      }
    }
  }
  return best!;
}
