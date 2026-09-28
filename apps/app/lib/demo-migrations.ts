/** Privacy migration for device-local demo data only. Never run on real profiles. */
const replacements: readonly (readonly [string, string])[] = [
  ["\u540d\u53e4\u5c4b\u5e02 \u6e2f\u533a", "サンプルエリアA"],
  ["\u540d\u53e4\u5c4b\u5e02\u4e2d\u5ddd\u533a", "サンプルエリアB"],
  ["\u540d\u53e4\u5c4b\u5e02\u6e2f\u533a", "サンプルエリアA"],
  ["\u540d\u53e4\u5c4b\u5e02", "サンプルエリアA"],
  ["\u6e2f\u533a\u30fb\u7269\u6d41", "物流チーム"],
  ["\u4e2d\u5ddd\u30ea\u30d0\u30fc\u30b5\u30a4\u30c9\u30b9\u30bf\u30b8\u30aa", "サンプルイベント会場"],
  ["\u307f\u306a\u3068\u30d9\u30a4\u7269\u6d41\u30e9\u30dc", "サンプル物流センター"],
  ["\u7d50\u57ce \u306f\u308b", "Aさん"],
  ["\u9752\u4e95 \u308a\u304a", "Bさん"],
  ["\u5c0f\u91ce \u305d\u3046", "Cさん"],
  ["\u702c\u6238 \u306a\u3064", "Dさん"],
  ["\u6e2f\u533a", "サンプルエリアA"],
  ["\u4e2d\u5ddd\u533a", "サンプルエリアB"],
  ["\u71b1\u7530\u533a", "サンプルエリアC"],
  ["\u9031\u672b\u306e\u8857\u306b\u3001\u3072\u3068\u3064\u306e\u304d\u3063\u304b\u3051\u3092\u3002", "住宅街でチラシのポスティング"],
  ["\u671d\u306e3\u6642\u9593\u3002\u7269\u6d41\u30c1\u30fc\u30e0\u306e\u4ef2\u9593\u52df\u96c6", "生活雑貨の仕分け・梱包（午前3時間）"],
  ["\u30a4\u30d9\u30f3\u30c8\u306e\u300c\u697d\u3057\u304b\u3063\u305f\u300d\u3092\u3064\u304f\u308b", "地域イベントの受付・会場準備"]
];
export function migrateDemo<T>(value:T):T {
 const visit=(item:unknown):unknown=>{
  if(typeof item==='string')return replacements.reduce((text,[before,after])=>text.split(before).join(after),item).replace(/([A-D]さん)さん/g,'$1');
  if(Array.isArray(item))return item.map(visit);
  if(item && typeof item==='object')return Object.fromEntries(Object.entries(item).map(([key,data])=>[key,visit(data)]));
  return item;
 };
 return visit(value) as T;
}
export function isDemoSnapshot(value:unknown):value is Record<string,Record<string,unknown>[]> {
 return !!value && typeof value==='object' && !Array.isArray(value) &&
  Object.values(value).every(rows=>Array.isArray(rows) && rows.every(row=>row && typeof row==='object' && !Array.isArray(row)));
}
