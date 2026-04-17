import { isNil, isEmpty } from 'ramda'

export const isPresent = data => !isNil(data) && !isEmpty(data)
