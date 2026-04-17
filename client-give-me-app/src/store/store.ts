import { configureStore } from '@reduxjs/toolkit';
import createSagaMiddleware from 'redux-saga';
import { all } from 'redux-saga/effects';

import catalogReducer from './catalogSlice';
import productReducer from './productSlice';
import basketItemReducer from './basketItemSlice';
import orderReducer from './orderSlice';
import catalogSaga from './catalogSaga';
import productSaga from "@/store/productSaga";
import basketItemSaga from "@/store/basketItemSaga";
import orderSaga from "@/store/orderSaga";
import novaPoshtaReducer from "@/store/novaPoshtaSlice";
import promocodeReducer from "@/store/promocodeSlice";
import userReducer from "@/store/userSlice";
import novaPoshtaSaga from "@/store/novaPoshtaSaga";
import promocodeSaga from "@/store/promocodeSaga";
import userSaga from "@/store/userSaga";
import favoriteReducer from './favoriteSlice';

const sagaMiddleware = createSagaMiddleware();

function* rootSaga() {
    yield all([catalogSaga(), productSaga(), basketItemSaga(), orderSaga(), novaPoshtaSaga(), promocodeSaga(), userSaga()]);
}

export const store = configureStore({
    reducer: {
        catalog: catalogReducer,
        product: productReducer,
        basketItem: basketItemReducer,
        order: orderReducer,
        novaPoshta: novaPoshtaReducer,
        promocode: promocodeReducer,
        user: userReducer,
        favorite: favoriteReducer,
    },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(sagaMiddleware),
});

sagaMiddleware.run(rootSaga);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
