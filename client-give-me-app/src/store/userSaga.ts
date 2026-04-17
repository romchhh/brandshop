import {call, put, takeLatest} from 'redux-saga/effects';
import axios from 'axios';

import {API_HOST} from "@/lib/constants";
import {fetchUserRequest, fetchUserSuccess} from "@/store/userSlice";

function* fetchUserSaga(action) {
    const {userId} = action.payload

    try {
        const response = yield call(axios.get, `${API_HOST}/api/user-metadata`,
            {headers: {'ngrok-skip-browser-warning': 'test'}, params: {userId}}
        );
        yield put(fetchUserSuccess(response.data));
    } catch (error) {
    }
}

export default function* userSaga() {
    yield takeLatest(fetchUserRequest.type, fetchUserSaga);
}
