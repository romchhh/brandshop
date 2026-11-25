import { pathOr } from 'ramda'

const WEB_UID_KEY = 'brandshop_web_uid'

/** Стабільний ID гостя на сайті (діапазон поза типовими Telegram id). */
export function getOrCreateWebUserId(): number {
  if (typeof window === 'undefined') {
    return 2_100_000_000
  }
  try {
    const existing = window.localStorage.getItem(WEB_UID_KEY)
    if (existing && /^\d+$/.test(existing)) {
      return Number(existing)
    }
    const id = 2_100_000_000 + Math.floor(Math.random() * 700_000_000)
    window.localStorage.setItem(WEB_UID_KEY, String(id))
    return id
  } catch {
    return 2_100_000_000
  }
}

/**
 * У міні-апі Telegram — user.id.
 * На сайті (mockEnv ставить ____mocked) — окремий guest id у localStorage (свій кошик на пристрій).
 */
export const getUserId = (initData: unknown): number => {
  if (typeof window !== 'undefined') {
    try {
      if (sessionStorage.getItem('____mocked') === '1') {
        return getOrCreateWebUserId()
      }
    } catch {
      /* ignore */
    }
  }
  const tgId = pathOr(null, ['user', 'id'], initData as object)
  if (tgId != null) {
    return Number(tgId)
  }
  return getOrCreateWebUserId()
}
