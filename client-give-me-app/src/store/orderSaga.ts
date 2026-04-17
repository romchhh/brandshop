import { call, put, takeLatest } from 'redux-saga/effects';
import axios from 'axios';
import { push } from 'react-router-redux';

import {API_HOST} from "@/lib/constants";
import {
    fetchOrdersSuccess,
    fetchOrdersRequest,
    createOrderRequest
} from "@/store/orderSlice";
import {resetBasketItems} from "@/store/basketItemSlice";

function* fetchOrdersSaga(action) {
    const { status, userId } = action.payload

    try {
        const response = yield call(axios.get, `${API_HOST}/api/user/${userId}/orders`, {headers: {'ngrok-skip-browser-warning': 'test'}, params: { status }});
        yield put(fetchOrdersSuccess(response.data));
    } catch (error) {
    }
}

function* createOrderSaga(action) {
    const { userId, onRedirect, city, warehouse, phoneNumber, fullName, paymentMethod, promocodeId, notes, deliveryMethod } = action.payload
    try {
        const params = {
            phone_number: `+380${phoneNumber}`,
            full_name: fullName,
            payment_method: paymentMethod,
            delivery_method: deliveryMethod,
            promocode_id: promocodeId,
            notes
        };

        // Додаємо поля міста та відділення тільки якщо це доставка Новою Поштою
        if (deliveryMethod === 'Нова пошта') {
            params.city = city;
            params.warehouse = warehouse;
        }

        const response = yield call(axios.post, `${API_HOST}/api/user/${userId}/orders/`, {
            headers: {'ngrok-skip-browser-warning': 'test'},
            params
        });
        
        yield put(resetBasketItems());
        onRedirect(response.data.invoice_url);
    } catch (error) {
        onRedirect(null);
    }
}

export default function* orderSaga() {
    yield takeLatest(fetchOrdersRequest.type, fetchOrdersSaga);
    yield takeLatest(createOrderRequest.type, createOrderSaga);
}
