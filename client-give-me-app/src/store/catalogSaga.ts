import { call, put, takeLatest } from 'redux-saga/effects';
import {
    fetchCatalogsRequest,
    fetchCatalogsSuccess,
    fetchCatalogsFailure,
    fetchCatalogSuccess,
    fetchCatalogFailure, fetchCatalogRequest
} from './catalogSlice';
import axios from 'axios';
import { API_HOST, LIST_PAGE_SIZE } from "@/lib/constants";
import { buildListCacheKey, readApiCache, writeApiCache } from '@/lib/apiCache';

function* fetchCatalogsSaga(action: { payload?: { page?: number; append?: boolean } }) {
    try {
        const page = action.payload?.page ?? 1;
        const append = !!action.payload?.append;
        const params = { summary: 1, page, page_size: LIST_PAGE_SIZE };
        const cacheKey = buildListCacheKey('catalogs', params);
        const hit = readApiCache(cacheKey);
        if (hit) {
            if (Array.isArray(hit)) {
                yield put(fetchCatalogsSuccess({ results: hit, append, next: false }));
                return;
            }
            if (typeof hit === 'object') {
                const body = hit as { results?: any[]; next?: boolean };
                yield put(
                    fetchCatalogsSuccess({
                        results: body.results ?? [],
                        append,
                        next: !!body.next,
                    }),
                );
                return;
            }
        }
        const response = yield call(axios.get, `${API_HOST}/api/catalogs/`, {
            headers: { 'ngrok-skip-browser-warning': 'test' },
            params,
        });
        const data = response.data;
        writeApiCache(cacheKey, data);
        const results = Array.isArray(data) ? data : data.results ?? [];
        const next = Array.isArray(data) ? false : !!data.next;
        yield put(fetchCatalogsSuccess({ results, append, next }));
    } catch (error: any) {
        yield put(fetchCatalogsFailure(error?.message || 'Network error'));
    }
}

function* fetchCatalogSaga(action) {
    try {
        const p = action.payload;
        const id = typeof p === 'object' && p !== null ? p.id : p;
        const page = typeof p === 'object' && p !== null ? (p.page || 1) : 1;
        const append = typeof p === 'object' && p !== null && !!p.append;
        const params = { paginated: 1, page, page_size: LIST_PAGE_SIZE };
        const cacheKey = buildListCacheKey(`catalogs/${id}`, params);
        const hit = readApiCache(cacheKey);
        if (hit) {
            yield put(
                fetchCatalogSuccess({
                    catalog: hit,
                    append,
                    id: Number(id),
                }),
            );
            return;
        }
        const response = yield call(axios.get, `${API_HOST}/api/catalogs/${id}`, {
            headers: { 'ngrok-skip-browser-warning': 'test' },
            params,
        });
        writeApiCache(cacheKey, response.data);
        yield put(
            fetchCatalogSuccess({
                catalog: response.data,
                append,
                id: Number(id),
            }),
        );
    } catch (error: any) {
        yield put(fetchCatalogFailure(error?.message || 'Network error'));
    }
}

export default function* catalogSaga() {
    yield takeLatest(fetchCatalogsRequest.type, fetchCatalogsSaga);
    yield takeLatest(fetchCatalogRequest.type, fetchCatalogSaga);
}
