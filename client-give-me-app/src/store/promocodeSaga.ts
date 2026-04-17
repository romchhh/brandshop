import { call, put, takeLatest } from 'redux-saga/effects';
import axios from 'axios';

import {API_HOST} from "@/lib/constants";
import {
    createBasketItemRequest,
    deleteBasketItemRequest,
    deleteBasketItemSuccess,
    fetchBasketItemsRequest,
    fetchBasketItemsSuccess,
    updateBasketItemRequest,
    updateBasketItemSuccess
} from "@/store/basketItemSlice";
import {fetchPromocodeRequest, fetchPromocodeSuccess} from "@/store/promocodeSlice";

function* fetchPromocodeSaga(action) {
    const { userId, promocode } = action.payload

    try {
        const response = yield call(axios.get, `${API_HOST}/api/promocode`,
            {headers: {'ngrok-skip-browser-warning': 'test'}, params: { userId, promocode }}
        );
        yield put(fetchPromocodeSuccess(response.data));
    } catch (error) {
    }
}

export default function* promocodeSaga() {
    yield takeLatest(fetchPromocodeRequest.type, fetchPromocodeSaga);
}
