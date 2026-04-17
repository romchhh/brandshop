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
        const response = yield call(axios.get, `${API_HOST}/api/catalogs/${action.payload}`, {headers: {'ngrok-skip-browser-warning': 'test'}}); // Replace with your actual API endpoint
        yield put(fetchCatalogSuccess(response.data));
    } catch (error) {
        yield put(fetchCatalogFailure(error.message));
    }
}

export default function* catalogSaga() {
    yield takeLatest(fetchCatalogsRequest.type, fetchCatalogsSaga);
    yield takeLatest(fetchCatalogRequest.type, fetchCatalogSaga);
}
