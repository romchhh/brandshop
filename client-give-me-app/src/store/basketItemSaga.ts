import { call, put, takeLatest } from 'redux-saga/effects';
import axios from 'axios';

import {API_HOST} from "@/lib/constants";
import {
    createBasketItemRequest,
    deleteBasketItemRequest,
    deleteBasketItemSuccess,
    fetchBasketItemsRequest,
    fetchBasketItemsSuccess, setBasketItemSuccess,
    updateBasketItemRequest,
    updateBasketItemSuccess
} from "@/store/basketItemSlice";
import {fetchUserRequest} from "@/store/userSlice";

function* fetchBasketItemsSaga(action) {
    try {
        const response = yield call(axios.get, `${API_HOST}/api/user/${action.payload}/basket-items`, {headers: {'ngrok-skip-browser-warning': 'test'}}); // Replace with your actual API endpoint
        yield put(fetchBasketItemsSuccess(response.data));
    } catch (error) {
    }
}

function* updateBasketItemSaga(action) {
    const { basketItem, userId, offset } = action.payload
    const quantity = basketItem.quantity + offset
    if ((quantity >= 100 ) || (quantity <= 0)) {
        return
    }
    try {
        yield call(axios.put, `${API_HOST}/api/user/${userId}/basket-items/${basketItem.id}/`, {headers: {'ngrok-skip-browser-warning': 'test'}, params: { quantity }});
        yield put(updateBasketItemSuccess({id: basketItem.id, quantity}))
        yield put(fetchUserRequest({userId}))
    } catch (error) {
    }
}

function* deleteBasketItemSaga(action) {
    const { basketItem, userId } = action.payload
    try {
        yield call(axios.delete, `${API_HOST}/api/user/${userId}/basket-items/${basketItem.id}/`, {headers: {'ngrok-skip-browser-warning': 'test'}});
        yield put(deleteBasketItemSuccess({id: basketItem.id}))
    } catch (error) {
    }
}

function* createBasketItemSaga(action) {
    const { userId, productId, productPropertyId, onSuccess } = action.payload
    try {
        const response = yield call(axios.post, `${API_HOST}/api/user/${userId}/basket-items/`,
            {headers: {'ngrok-skip-browser-warning': 'test'},
                params: { product_id: productId, product_property_id: productPropertyId }});
        yield put(setBasketItemSuccess(response.data));
        yield put(fetchUserRequest({userId}))
    } catch (error) {
    }
}

export default function* basketItemSaga() {
    yield takeLatest(fetchBasketItemsRequest.type, fetchBasketItemsSaga);
    yield takeLatest(updateBasketItemRequest.type, updateBasketItemSaga);
    yield takeLatest(deleteBasketItemRequest.type, deleteBasketItemSaga);
    yield takeLatest(createBasketItemRequest.type, createBasketItemSaga);
}
