import { call, put, takeLatest } from 'redux-saga/effects';
import {
    fetchProductSuccess,
    fetchProductRequest,
    fetchViewProductsSuccess,
    fetchViewProductsRequest,
    fetchPromotionalProductsSuccess,
    fetchPromotionalProductsRequest,
    fetchPromotionalProductsFailure,
} from './productSlice';
import axios from 'axios';
import { API_HOST, LIST_PAGE_SIZE } from "@/lib/constants";
import { buildListCacheKey, readApiCache, writeApiCache } from '@/lib/apiCache';


function* fetchProductSaga(action) {
    try {
        const { productId, userId } = action.payload;
        const cacheKey = buildListCacheKey(`products/${productId}`, { userId: userId || 0 });
        const hit = readApiCache(cacheKey);
        if (hit) {
            yield put(fetchProductSuccess(hit));
            return;
        }
        const url = `${API_HOST}/api/products/${productId}`;
        const response = yield call(axios.get, url, {
            headers: { "ngrok-skip-browser-warning": "test" },
            params: { userId },
        });
        writeApiCache(cacheKey, response.data);
        yield put(fetchProductSuccess(response.data));
    } catch (error) {
        /* сторінка лишається на лоадері; повторний захід перезапитає */
    }
}

function* fetchViewProductsSaga(action: { payload: number | { userId: number; page?: number; append?: boolean } }) {
    try {
        const pl = action.payload;
        const userId = typeof pl === 'object' ? pl.userId : pl;
        const page = typeof pl === 'object' ? pl.page ?? 1 : 1;
        const append = typeof pl === 'object' && !!pl.append;
        const params = { page, page_size: LIST_PAGE_SIZE };
        const cacheKey = buildListCacheKey('viewed-products', { userId, ...params });
        const hit = readApiCache(cacheKey);
        if (hit && typeof hit === 'object' && !Array.isArray(hit)) {
            yield put(fetchViewProductsSuccess({ ...(hit as object), append }));
            return;
        }
        const response = yield call(axios.get, `${API_HOST}/api/user/${userId}/viewed-products`, {
            headers: { 'ngrok-skip-browser-warning': 'test' },
            params,
        });
        writeApiCache(cacheKey, response.data);
        const data = response.data;
        const results = Array.isArray(data) ? data : data.results ?? [];
        const next = Array.isArray(data) ? false : !!data.next;
        yield put(fetchViewProductsSuccess({ results, append, next }));
    } catch (error) {
    }
}

function* fetchPromotionalProductsSaga(action: { payload?: { page?: number; append?: boolean; pageSize?: number } }) {
    try {
        const p = action.payload || {};
        const page = p.page || 1;
        const append = !!p.append;
        const params = { page, page_size: p.pageSize || LIST_PAGE_SIZE };
        const cacheKey = buildListCacheKey('promotional-products', params);
        const hit = readApiCache(cacheKey);
        if (hit && typeof hit === 'object') {
            yield put(
                fetchPromotionalProductsSuccess({
                    ...(hit as object),
                    append,
                }),
            );
            return;
        }
        const response = yield call(axios.get, `${API_HOST}/api/promotional-products`, {
            headers: { 'ngrok-skip-browser-warning': 'test' },
            params,
        });
        writeApiCache(cacheKey, response.data);
        yield put(
            fetchPromotionalProductsSuccess({
                ...response.data,
                append,
            }),
        );
    } catch {
        yield put(fetchPromotionalProductsFailure());
    }
}

export default function* productSaga() {
    yield takeLatest(fetchProductRequest.type, fetchProductSaga);
    yield takeLatest(fetchViewProductsRequest.type, fetchViewProductsSaga);
    yield takeLatest(fetchPromotionalProductsRequest.type, fetchPromotionalProductsSaga);
}
