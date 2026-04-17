import { call, put, takeLatest } from 'redux-saga/effects';
import {
    fetchProductSuccess,
    fetchProductRequest,
    fetchViewProductsSuccess,
    fetchViewProductsRequest,
    fetchPromotionalProductsSuccess,
    fetchPromotionalProductsRequest,
} from './productSlice';
import axios from 'axios';
import {API_HOST} from "@/lib/constants";

function* fetchProductSaga(action) {
    try {
        const { productId, userId } = action.payload
        const response = yield call(axios.get, `${API_HOST}/api/products/${productId}`, {headers: {'ngrok-skip-browser-warning': 'test'}, params: {userId}}); // Replace with your actual API endpoint
        yield put(fetchProductSuccess(response.data));
    } catch (error) {
    }
}

function* fetchViewProductsSaga(action) {
    try {
        const response = yield call(axios.get, `${API_HOST}/api/user/${action.payload}/viewed-products`, {headers: {'ngrok-skip-browser-warning': 'test'}}); // Replace with your actual API endpoint
        yield put(fetchViewProductsSuccess(response.data));
    } catch (error) {
    }
}

function* fetchPromotionalProductsSaga() {
    try {
        const response = yield call(axios.get, `${API_HOST}/api/promotional-products`, {headers: {'ngrok-skip-browser-warning': 'test'}}); // Replace with your actual API endpoint
        yield put(fetchPromotionalProductsSuccess(response.data));
    } catch (error) {
    }
}

export default function* productSaga() {
    yield takeLatest(fetchProductRequest.type, fetchProductSaga);
    yield takeLatest(fetchViewProductsRequest.type, fetchViewProductsSaga);
    yield takeLatest(fetchPromotionalProductsRequest.type, fetchPromotionalProductsSaga);
}
