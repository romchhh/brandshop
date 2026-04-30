import { call, put, takeLatest } from 'redux-saga/effects';
import {
    fetchCatalogsRequest,
    fetchCatalogsSuccess,
    fetchCatalogsFailure,
    fetchCatalogSuccess,
    fetchCatalogFailure, fetchCatalogRequest
} from './catalogSlice';
import axios from 'axios';
import {API_HOST} from "@/lib/constants";
import { buildListCacheKey, readApiCache, writeApiCache } from '@/lib/apiCache';

const CATALOG_PAGE_SIZE = 20;

function* fetchCatalogsSaga() {
    try {
        const response = yield call(axios.get, `${API_HOST}/api/catalogs`, {headers: {'ngrok-skip-browser-warning': 'test'}}); // Replace with your actual API endpoint
        yield put(fetchCatalogsSuccess(response.data));
    } catch (error) {
        yield put(fetchCatalogsFailure(error.message));
    }
}

function* fetchCatalogSaga(action) {
    try {
        const p = action.payload;
        const id = typeof p === 'object' && p !== null ? p.id : p;
        const page = typeof p === 'object' && p !== null ? (p.page || 1) : 1;
        const append = typeof p === 'object' && p !== null && !!p.append;
        const params = { paginated: 1, page, page_size: CATALOG_PAGE_SIZE };
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
