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
import {API_HOST} from "@/lib/constants";
import { buildListCacheKey, readApiCache, writeApiCache } from '@/lib/apiCache';

const PROMO_PAGE_SIZE = 20;

function* fetchProductSaga(action) {
    try {
        const { productId, userId } = action.payload;
        const url = `${API_HOST}/api/products/${productId}`;
        const response = yield call(axios.get, url, {
            headers: { "ngrok-skip-browser-warning": "test" },
            params: { userId },
        });
        const data = response.data;
        console.log("[BrandShop] Товар з API OK", {
            requestUrl: url,
            API_HOST,
            productId,
            photo: data?.photo ?? null,
            product_properties_photos:
                data?.product_properties?.map((p: { id: number; title: string; photo?: string }) => ({
                    id: p.id,
                    title: p.title,
                    photo: p.photo ?? null,
                })) ?? [],
        });
        yield put(fetchProductSuccess(data));
    } catch (error) {
        console.error("[BrandShop] Товар з API помилка", {
            productId: action.payload?.productId,
            API_HOST,
            error,
        });
    }
}

function* fetchViewProductsSaga(action) {
    try {
        const response = yield call(axios.get, `${API_HOST}/api/user/${action.payload}/viewed-products`, {headers: {'ngrok-skip-browser-warning': 'test'}}); // Replace with your actual API endpoint
        yield put(fetchViewProductsSuccess(response.data));
    } catch (error) {
    }
}

function* fetchPromotionalProductsSaga(action: { payload?: { page?: number; append?: boolean; pageSize?: number } }) {
    try {
        const p = action.payload || {};
        const page = p.page || 1;
        const append = !!p.append;
        const pageSize = p.pageSize || PROMO_PAGE_SIZE;
        const params = { page, page_size: pageSize };
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
