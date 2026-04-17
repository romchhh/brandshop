import { pathOr } from 'ramda'

export const getUserId = (initData) => pathOr(1, ['user', 'id'], initData)
