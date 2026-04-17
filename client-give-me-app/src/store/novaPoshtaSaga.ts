import {call, put, takeLatest} from 'redux-saga/effects';
import axios from 'axios';
import { pathOr } from 'ramda'

import {
    fetchCitiesSuccess,
    fetchWarehousesSuccess,
    fetchCitiesRequest,
    fetchWarehousesRequest
} from "@/store/novaPoshtaSlice";

function* fetchCitiesSaga(action) {
    const {cityName} = action.payload

    try {
        const response = yield call(axios.post, `https://api.novaposhta.ua/v2.0/json/ `, {
                "apiKey": "",
                "modelName": "AddressGeneral",
                "calledMethod": "searchSettlements",
                "methodProperties": {
                    "CityName": cityName,
                    "Limit": "10",
                    "Page": "1"
                }
        });
        yield put(fetchCitiesSuccess(response.data.success ? pathOr([], ['data', 'data', 0, 'Addresses'], response) : []));
    } catch (error) {
    }
}

function* fetchWarehousesSaga(action) {
    const {cityRef, search} = action.payload

    try {
        const response = yield call(axios.post, `https://api.novaposhta.ua/v2.0/json/ `,
            {
                "apiKey": "",
                "modelName": "AddressGeneral",
                "calledMethod": "getWarehouses",
                "methodProperties": {
                    "FindByString": search,
                    "CityRef" : cityRef,
                    "Limit": "50",
                    "Page": "1",
                    "Language" : "UA"
                }
        });
        yield put(fetchWarehousesSuccess(response.data.success ? response.data.data : []));
    } catch (error) {
    }
}

export default function* novaPoshtaSaga() {
    yield takeLatest(fetchCitiesRequest.type, fetchCitiesSaga);
    yield takeLatest(fetchWarehousesRequest.type, fetchWarehousesSaga);
}
